#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Views tests for the OSF.'''

from __future__ import absolute_import
import datetime as dt
import mock
import httplib as http
from dateutil.parser import parse as parse_date

from nose.tools import *  # noqa PEP8 asserts

from modularodm import Q

from framework.mongo import database

from website.models import Node, MetaSchema, DraftRegistration
from website.project.metadata.schemas import ACTIVE_META_SCHEMAS

from tests.base import OsfTestCase
from tests.factories import (
    NodeFactory, AuthUserFactory, DraftRegistrationFactory
)
from tests.test_registrations.base import RegistrationsTestBase


class TestRegistrationViews(OsfTestCase):
    # TODO: do these already exist?
    pass


class TestDraftRegistrationViews(RegistrationsTestBase):

    def tearDown(self):
        super(TestDraftRegistrationViews, self).tearDown()
        DraftRegistration.remove()

    def test_submit_draft_for_review(self):
        url = self.draft_api_url('submit_draft_for_review')
        res = self.app.post_json(
            url,
            self.embargo_payload,
            auth=self.user.auth
        )
        assert_equal(res.status_code, http.ACCEPTED)
        data = res.json
        assert_in('status', data)
        assert_equal(data['status'], 'initiated')

        self.draft.reload()
        assert_is_not_none(self.draft.approval)
        assert_equal(self.draft.approval.meta, {
            u'registration_choice': unicode(self.embargo_payload['registrationChoice']),
            u'embargo_end_date': unicode(self.embargo_payload['embargoEndDate'])
        })

    def test_submit_draft_for_review_non_admin(self):
        url = self.draft_api_url('submit_draft_for_review')
        res = self.app.post_json(
            url,
            self.embargo_payload,
            auth=self.non_admin.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.FORBIDDEN)

    @mock.patch('website.project.model.DraftRegistration.register', autospec=True)
    def test_register_draft_registration(self, mock_register_draft):

        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        res = self.app.post_json(url, {
            'registrationChoice': 'Make registration public immediately'
        }, auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        assert_equal(mock_register_draft.call_args[0][0]._id, self.draft._id)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_template_make_public_creates_pending_registration(self, mock_enquque):
        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        res = self.app.post_json(url, {'registrationChoice': 'immediate'}, auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Most recent node is a registration
        reg = Node.load(self.node.node__registrations[-1])
        assert_true(reg.is_registration)
        # The registration created is public
        assert_true(reg.is_pending_registration)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_template_make_public_makes_children_pending_registration(self, mock_enqueue):
        comp1 = NodeFactory(parent=self.node)
        NodeFactory(parent=comp1)

        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        res = self.app.post_json(url, {'registrationChoice': 'immediate'}, auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Most recent node is a registration
        reg = Node.load(self.node.node__registrations[-1])
        for node in reg.get_descendants_recursive():
            assert_true(node.is_registration)
            assert_true(node.is_pending_registration)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_with_embargo_creates_embargo(self, mock_enquque):
        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        res = self.app.post_json(
            url,
            {
                'registrationChoice': 'embargo',
                'embargoEndDate': "Fri, 01 Jan {year} 05:00:00 GMT".format(year=str(dt.date.today().year + 1))
            },
            auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Most recent node is a registration
        reg = Node.load(self.node.node__registrations[-1])
        assert_true(reg.is_registration)
        # The registration created is not public
        assert_false(reg.is_public)
        # The registration is pending an embargo that has not been approved
        assert_true(reg.is_pending_embargo)
        assert_false(reg.embargo_end_date)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_with_embargo_adds_to_parent_project_logs(self, mock_enquque):
        initial_project_logs = len(self.node.logs)
        res = self.app.post_json(
            self.node.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.embargo_payload,
            content_type='application/json',
            auth=self.user.auth
        )

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Logs: Created, registered, embargo initiated
        assert_equal(len(self.node.logs), initial_project_logs + 1)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_with_embargo_is_not_public(self, mock_enqueue):
        res = self.app.post_json(
            self.node.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.embargo_payload,
            content_type='application/json',
            auth=self.user.auth
        )

        assert_equal(res.status_code, http.ACCEPTED)

        registration = Node.find().sort('-registered_date')[0]

        assert_true(registration.is_registration)
        assert_false(registration.is_public)
        assert_true(registration.is_pending_embargo)
        assert_is_not_none(registration.embargo)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_invalid_embargo_end_date_raises_HTTPError(self, mock_enqueue):
        res = self.app.post_json(
            self.node.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.invalid_embargo_date_payload,
            content_type='application/json',
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_get_draft_registrations_only_gets_drafts_for_that_node(self):
        dummy = NodeFactory()

        # Drafts for dummy node
        for i in range(5):
            d = DraftRegistrationFactory(
                initiator=self.user,
                branched_from=dummy,
                meta_schema=self.meta_schema,
                schema_data={}
            )

        found = [self.draft]
        # Drafts for self.node
        for i in range(3):
            d = DraftRegistrationFactory(
                initiator=self.user,
                branched_from=self.node,
                meta_schema=self.meta_schema,
                schema_data={}
            )
            found.append(d)
        url = self.node.api_url_for('get_draft_registrations')

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        # 3 new, 1 from setUp
        assert_equal(len(res.json['drafts']), 4)
        for draft in res.json['drafts']:
            assert_in(draft['pk'], [f._id for f in found])

    def test_new_draft_registration(self):
        target = NodeFactory(creator=self.user)
        payload = {
            'schema_name': 'Open-Ended Registration',
            'schema_version': 1
        }
        url = target.web_url_for('new_draft_registration')

        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, http.FOUND)
        draft = DraftRegistration.find_one(Q('branched_from', 'eq', target))
        assert_equal(draft.registration_schema, self.meta_schema)

    def test_update_draft_registration(self):
        metadata = {
            'summary': {
                'value': 'updated',
                'comments': []
            }
        }
        assert_not_equal(metadata, self.draft.registration_metadata)
        payload = {
            'schema_data': metadata,
            'schema_name': 'OSF-Standard Pre-Data Collection Registration',
            'schema_version': 1
        }
        url = self.node.api_url_for('update_draft_registration', draft_id=self.draft._id)

        res = self.app.put_json(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)

        open_ended_schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', 1)
        )
        self.draft.reload()
        assert_equal(open_ended_schema, self.draft.registration_schema)
        assert_equal(metadata, self.draft.registration_metadata)

    def test_delete_draft_registration(self):
        assert_equal(1, DraftRegistration.find().count())
        url = self.node.api_url_for('delete_draft_registration', draft_id=self.draft._id)

        res = self.app.delete(url, auth=self.user.auth)
        assert_equal(res.status_code, http.NO_CONTENT)
        assert_equal(0, DraftRegistration.find().count())

    def test_only_admin_can_delete_registration(self):
        non_admin = AuthUserFactory()
        assert_equal(1, DraftRegistration.find().count())
        url = self.node.api_url_for('delete_draft_registration', draft_id=self.draft._id)

        res = self.app.delete(url, auth=non_admin.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)
        assert_equal(1, DraftRegistration.find().count())

    def test_get_metaschemas(self):
        url = '/api/v1/project/drafts/schemas/'
        res = self.app.get(url).json
        assert_equal(len(res['meta_schemas']), len(ACTIVE_META_SCHEMAS))

        url = '/api/v1/project/drafts/schemas/?include=all'
        res = self.app.get(url)
        assert_equal(res.status_code, http.OK)
        assert_equal(len(res.json['meta_schemas']), len(
            [
                schema for schema in MetaSchema.find()
                if schema.name in ACTIVE_META_SCHEMAS
            ]
        ))
