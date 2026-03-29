{
    'name': 'Agentic Brain Theme',
    'description': 'Custom theme for Agentic Brain Solutions',
    'version': '1.0',
    'depends': ['website', 'crm'],
    'data': [
        'views/layout.xml',
        'views/homepage.xml',
        'views/about.xml',
        'views/contact.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'theme_agenticbrain/static/src/scss/theme.scss',
        ],
    },
    'application': False,
    'license': 'LGPL-3',
}
