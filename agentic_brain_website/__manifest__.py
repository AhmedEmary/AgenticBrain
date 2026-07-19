{
    "name": "Agentic Brain Website",
    "version": "1.0.0",
    "category": "Website",
    "summary": "Modern, animated homepage for Agentic Brain Solutions",
    "description": """
Replaces the website homepage with a modern, premium design for
Agentic Brain Solutions (Odoo ERP + autonomous AI agents).
Includes the hero, services, workflow, AI-agents section, animated
stats, process, testimonial, CTA and footer — all self-contained.
    """,
    "author": "Agentic Brain Solutions",
    "website": "https://agenticbrain.tech",
    "depends": ["website"],
    "data": [
        "views/homepage.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "agentic_brain_website/static/src/css/style.css",
            "agentic_brain_website/static/src/js/main.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
