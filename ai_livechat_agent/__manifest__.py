{
    'name': 'AI Livechat Agent',
    'version': '1.0',
    'category': 'Website/Livechat',
    'summary': 'Replaces human live chat operators with a Gemini AI agent.',
    'depends': ['base', 'mail', 'im_livechat'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_agent_views.xml',
    ],
    'installable': True,
    'application': False,
    'author': 'Ahmed Elamery',
    'license': 'LGPL-3',
}