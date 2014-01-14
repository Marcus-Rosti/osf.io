from .model import AddonS3UserSettings,AddonS3NodeSettings
from .routes import settings_routes,page_routes

USER_SETTINGS_MODEL = AddonS3UserSettings
NODE_SETTINGS_MODEL = AddonS3NodeSettings

ROUTES = [settings_routes,page_routes]

SHORT_NAME = 's3'
FULL_NAME = 'Amazon Simple Storage Service'


OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['widget', 'page']
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [
        '/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js',
        '/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js',
        '/static/vendor/dropzone/dropzone.js',
        '/static/js/slickgrid.custom.min.js',
        '/static/js/hgrid.js',
        'hgrid-s3.js',
    ],
}

INCLUDE_CSS = {
    'widget': [],
        'page': ['/static/css/hgrid-base.css'],
}
'''

SCHEMA = {
    'pages': [
        {
            'id': 'null',
            'title': 'S3 Addon Settings',
            'contents': [
                {
                    'id': 'access_key',
                    'type': 'textfield',
                    'label': 'S3 Access Key',
                    'required': True,
                },
                {
                    'id': 'secret_key',
                    'type': 'textfield',
                    'label': 'S3 Secret Key',
                    'required': True,
                },
                {
                    'id': 's3_bucket',
                    'type': 'textfield',
                    'label': 'S3 Bucket Name',
                    'required': True,
                }
            ]
        }
    ]
}
'''