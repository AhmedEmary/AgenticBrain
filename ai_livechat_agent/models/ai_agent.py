from odoo import models, fields, api

class AIAgent(models.Model):
    _name = 'ai.agent'
    _description = 'AI Agent Configuration'

    name = fields.Char(string='Agent Name', required=True, help="e.g., Aisha Support, Mazen Sales")
    active = fields.Boolean(default=True)

    provider = fields.Selection([
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI ChatGPT'),
        ('anthropic', 'Anthropic Claude')
    ], string='AI Provider', default='gemini', required=True)

    api_key = fields.Char(string='API Key', required=True)
    endpoint_url = fields.Char(string='Custom Endpoint', help="Optional: Used for custom LLM servers or Azure.")
    model_name = fields.Char(string='Model Version', default='gemini-2.5-flash', required=True)

    system_prompt = fields.Text(string='System Prompt', help="The base instructions for how this agent should behave.")

    # 3. THE CRUCIAL LINK: Impersonating an Odoo User
    user_id = fields.Many2one('res.users', string='Related Odoo User', required=True,
                              help="The Odoo user account this AI will use to take actions in the database.")
