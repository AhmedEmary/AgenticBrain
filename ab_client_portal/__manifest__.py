{
    'name': 'Agentic Brain — Client Portal',
    'version': '1.0',
    'category': 'Services/Project',
    'summary': 'Client-facing project portal with intake/approval gate and AI-assisted triage.',
    'depends': ['project', 'portal', 'mail', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'security/ab_client_portal_security.xml',
        'data/project_task_type_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/mail_template_data.xml',
        'views/project_task_views.xml',
        'views/project_task_actions.xml',
        'views/portal_templates.xml',
    ],
    'external_dependencies': {
        'python': ['anthropic'],
    },
    'installable': True,
    'application': False,
    'author': 'Ahmed Elamery',
    'license': 'LGPL-3',
}
