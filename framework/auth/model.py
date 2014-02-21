# -*- coding: utf-8 -*-
import re
import itertools
import logging
import urlparse
import datetime as dt

import pytz
import bson

from framework.analytics import piwik
from framework.bcrypt import generate_password_hash, check_password_hash
from framework import fields, Q, analytics
from framework.guid.model import GuidStoredObject
from framework.search import solr
from framework.addons import AddonModelMixin
from framework.auth import utils

from website import settings, filters, security

name_formatters = {
   'long': lambda user: user.fullname,
   'surname': lambda user: user.family_name if user.family_name else user.fullname,
   'initials': lambda user: u'{surname}, {initial}.'.format(
       surname=user.family_name,
       initial=user.given_name_initial
   ),
}

logger = logging.getLogger(__name__)


def generate_confirm_token():
    return security.random_string(30)


class User(GuidStoredObject, AddonModelMixin):

    redirect_mode = 'proxy'

    _id = fields.StringField(primary=True)

    # NOTE: In the OSF, username is an email
    username = fields.StringField(required=True)
    password = fields.StringField()
    fullname = fields.StringField(required=True)
    is_registered = fields.BooleanField()
    is_claimed = fields.BooleanField()  # TODO: Unused. Remove me?
    # The user who merged this account
    merged_by = fields.ForeignField('user', default=None, backref="merged")
    verification_key = fields.StringField()
    emails = fields.StringField(list=True)
    email_verifications = fields.DictionaryField()  # TODO: Unused. Remove me?
    aka = fields.StringField(list=True)
    date_registered = fields.DateTimeField(auto_now_add=dt.datetime.utcnow)
    # Watched nodes are stored via a list of WatchConfigs
    watched = fields.ForeignField("WatchConfig", list=True, backref="watched")

    # Recently added contributors stored via a list of users
    recently_added = fields.ForeignField("user", list=True, backref="recently_added")

    # CSL names
    given_name = fields.StringField()
    middle_names = fields.StringField()
    family_name = fields.StringField()
    suffix = fields.StringField()

    api_keys = fields.ForeignField('apikey', list=True, backref='keyed')

    piwik_token = fields.StringField()

    date_last_login = fields.DateTimeField()

    date_confirmed = fields.DateTimeField()

    _meta = {'optimistic' : True}

    def set_password(self, raw_password):
        '''Set the password for this user to the hash of ``raw_password``.'''
        self.password = generate_password_hash(raw_password)
        return None

    def check_password(self, raw_password):
        '''Return a boolean of whether ``raw_password`` was correct.'''
        if not self.password or not raw_password:
            return False
        return check_password_hash(self.password, raw_password)

    @classmethod
    def create_unconfirmed(cls, username, password, fullname):
        """Create a new user who has begun registration but needs to verify
        their primary email address (username).
        """
        parsed = utils.parse_name(fullname)
        user = cls(
            username=username,
            fullname=fullname,
            **parsed
        )
        user.set_password(password)
        user.add_email_verification(username)
        user.is_registered = False
        return user

    def add_email_verification(self, email):
        """Add an email verification token for a given email."""
        token = generate_confirm_token()
        self.email_verifications[token] = {'email': email}
        return token

    def get_confirmation_token(self, email):
        """Return the confirmation token for a given email.

        :raises: KeyError if there no token for the email
        """
        for token, info in self.email_verifications.items():
            if info['email'] == email:
                return token
        raise KeyError('No confirmation token for email {0!r}'.format(email))

    def get_confirmation_url(self, email, external=True):
        """Return the confirmation url for a given email.

        :raises: KeyError if there is no token for the email.
        """
        base = settings.DOMAIN if external else '/'
        token = self.get_confirmation_token(email)
        return "{0}confirm/{1}/{2}".format(base, self._primary_key, token)

    def verify_confirmation_token(self, token):
        """Return whether or not a confirmation token is valid for this user.
        """
        return token in self.email_verifications.keys()

    def confirm_email(self, token):
        if self.verify_confirmation_token(token):
            email = self.email_verifications[token]['email']
            self.emails.append(email)
            # Complete registration if primary email
            if email == self.username:
                self.is_registered = True
                self.date_confirmed = dt.datetime.utcnow()
            # Revoke token
            del self.email_verifications[token]
            self.save()
            return True
        else:
            return False

    @property
    def biblio_name(self):
        given_names = self.given_name + ' ' + self.middle_names
        surname = self.family_name
        if surname != given_names:
            initials = [
                name[0].upper() + '.'
                for name in given_names.split(' ')
                if name and re.search(r'\w', name[0], re.I)
            ]
            return u'{0}, {1}'.format(surname, ' '.join(initials))
        return surname

    @property
    def given_name_initial(self):
        """
        The user's preferred initialization of their given name.

        Some users with common names may choose to distinguish themselves from
        their colleagues in this way. For instance, there could be two
        well-known researchers in a single field named "Robert Walker".
        "Walker, R" could then refer to either of them. "Walker, R.H." could
        provide easy disambiguation.

        NOTE: The internal representation for this should never end with a
              period. "R" and "R.H" would be correct in the prior case, but
              "R.H." would not.
        """
        return self.given_name[0]

    @property
    def url(self):
        return '/{}/'.format(self._primary_key)

    @property
    def api_url(self):
        return '/api/v1/profile/{0}/'.format(self._primary_key)

    @property
    def absolute_url(self):
        return urlparse.urljoin(settings.DOMAIN, self.url)

    @property
    def display_absolute_url(self):
        url = self.absolute_url
        if url is not None:
            return re.sub(r'https?:', '', url).strip('/')

    @property
    def deep_url(self):
        return '/profile/{}/'.format(self._primary_key)

    @property
    def gravatar_url(self):
        return filters.gravatar(
                    self,
                    use_ssl=True,
                    size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
                )

    @property
    def activity_points(self):
        return analytics.get_total_activity_count(self._primary_key)

    @property
    def is_merged(self):
        '''Whether or not this account has been merged into another account.
        '''
        return self.merged_by is not None

    @property
    def profile_url(self):
        return '/{}/'.format(self._id)

    def get_summary(self, formatter='long'):
        return {
            'user_fullname': self.fullname,
            'user_profile_url': self.profile_url,
            'user_display_name': name_formatters[formatter](self),
        }

    def save(self, *args, **kwargs):
        rv = super(User, self).save(*args, **kwargs)
        self.update_solr()
        if settings.PIWIK_HOST and not self.piwik_token:
            try:
                piwik.create_user(self)
            except (piwik.PiwikException, ValueError):
                logger.error("Piwik user creation failed: " + self._id)
        return rv

    def update_solr(self):
        if not settings.USE_SOLR:
            return
        solr.update_user(self)

    @classmethod
    def find_by_email(cls, email):
        try:
            user = cls.find_one(
                Q('emails', 'eq', email)
            )
            return [user]
        except:
            return []

    def serialize(self):
        return {
            'id': self._primary_key,
            'fullname': self.fullname,
            'registered': self.is_registered,
            'url': self.url,
            'api_url': self.api_url,
        }

    ###### OSF-Specific methods ######

    def watch(self, watch_config, save=False):
        '''Watch a node by adding its WatchConfig to this user's ``watched``
        list. Raises ``ValueError`` if the node is already watched.

        :param watch_config: The WatchConfig to add.
        :param save: Whether to save the user.
        '''
        watched_nodes = [each.node for each in self.watched]
        if watch_config.node in watched_nodes:
            raise ValueError("Node is already being watched.")
        watch_config.save()
        self.watched.append(watch_config)
        if save:
            self.save()
        return None

    def unwatch(self, watch_config, save=False):
        '''Unwatch a node by removing its WatchConfig from this user's ``watched``
        list. Raises ``ValueError`` if the node is not already being watched.

        :param watch_config: The WatchConfig to remove.
        :param save: Whether to save the user.
        '''
        for each in self.watched:
            if watch_config.node._id == each.node._id:
                each.__class__.remove_one(each)
                if save:
                    self.save()
                return None
        raise ValueError('Node not being watched.')

    def is_watching(self, node):
        '''Return whether a not a user is watching a Node.'''
        watched_node_ids = set([config.node._id for config in self.watched])
        return node._id in watched_node_ids

    def get_recent_log_ids(self, since=None):
        '''Return a generator of recent logs' ids.

        :param since: A datetime specifying the oldest time to retrieve logs
        from. If ``None``, defaults to 60 days before today. Must be a tz-aware
        datetime because PyMongo's generation times are tz-aware.

        :rtype: generator of log ids (strings)
        '''
        log_ids = []
        # Default since to 60 days before today if since is None
        # timezone aware utcnow
        utcnow = dt.datetime.utcnow().replace(tzinfo=pytz.utc)
        since_date = since or (utcnow - dt.timedelta(days=60))
        for config in self.watched:
            # Extract the timestamps for each log from the log_id (fast!)
            # The first 4 bytes of Mongo's ObjectId encodes time
            # This prevents having to load each Log Object and access their
            # date fields
            node_log_ids = [log_id for log_id in config.node.logs._to_primary_keys()
                                   if bson.ObjectId(log_id).generation_time > since_date]
            # Log ids in reverse chronological order
            log_ids = _merge_into_reversed(log_ids, node_log_ids)
        return (l_id for l_id in log_ids)

    def get_daily_digest_log_ids(self):
        '''Return a generator of log ids generated in the past day
        (starting at UTC 00:00).
        '''
        utcnow = dt.datetime.utcnow()
        midnight = dt.datetime(utcnow.year, utcnow.month, utcnow.day,
                            0, 0, 0, tzinfo=pytz.utc)
        return self.get_recent_log_ids(since=midnight)

    def merge_user(self, user, save=False):
        '''Merge a registered user into this account. This user will be
        a contributor on any project

        :param user: A User object to be merged.
        '''
        # Inherit emails
        # TODO: Shouldn't import inside function call
        from .decorators import Auth
        self.emails.extend(user.emails)
        # Inherit projects the user was a contributor for
        for node in user.node__contributed:
            node.add_contributor(contributor=self, log=False)
            node.remove_contributor(
                contributor=user, auth=Auth(user=self), log=False
            )
            node.save()
        # Inherits projects the user created
        for node in user.node__created:
            node.creator = self
            node.save()
        user.merged_by = self
        user.save()
        if save:
            self.save()
        return None


def _merge_into_reversed(*iterables):
    '''Merge multiple sorted inputs into a single output in reverse order.
    '''
    return sorted(itertools.chain(*iterables), reverse=True)
