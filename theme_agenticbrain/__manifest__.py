{
    'name': 'Agentic Brain Theme',
    'description': 'Custom theme for Agentic Brain Solutions',
    'category': 'Theme/Corporate',
    'version': '1.0',
    'depends': ['website'],
    'data': [
        'views/layout.xml',
        'views/homepage.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'theme_agenticbrain/static/src/scss/primary_variables.scss',
        ],
    },
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
