{
    "name" : "WhiteLabel Themes",
    "category": "Hidden",
    "description":
        """
        WhiteLabel Theme.
        This module provides theme WhiteLabel branding for Odoo web client.
        """,
    'active': True,
    'depends': ['web'],
    'data': [
        'security/security.xml',
        'data.xml',
        'views.xml',
        'js.xml',
        'pre_install.yml'   
        ],
    'qweb': [
        'static/src/xml/template.xml',
    ],
    'installable': True
}
