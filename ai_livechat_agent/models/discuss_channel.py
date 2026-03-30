from odoo import models, api
from odoo.tools import html2plaintext
from odoo.addons.mail.tools.discuss import Store  # Add this import
from google import genai
import logging

_logger = logging.getLogger(__name__)

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def message_post(self, **kwargs):
        # 1. First, let Odoo save the human's message normally
        message = super(DiscussChannel, self).message_post(**kwargs)

        # 2. Check if this is a Livechat channel
        if self.channel_type != 'livechat':
            return message

        # 3. Prevent Infinite AI Loops!
        bot_user = self.env['res.users'].search([('name', '=', 'Support-ai')], limit=1)
        if not bot_user:
            _logger.warning("Aisha AI user not found! Please create a user named 'Aisha AI'.")
            return message

        if message.author_id.id == bot_user.partner_id.id:
            return message # Stop here if the author is Aisha

        # 4. If it's a real user message, trigger the AI
        if kwargs.get('message_type') == 'comment':
            clean_text = html2plaintext(message.body)
            # Pass BOTH the text and the bot_user to the function
            self._get_ai_response(clean_text, bot_user)

        return message

    def _get_ai_response(self, user_text, bot_user):
        # Fetch the agent config
        agent = self.env['ai.agent'].sudo().search([('name', '=', 'support-AI')], limit=1)

        if not agent:
            _logger.error("AI Agent 'Aisha AI' not found in the database!")
            return

        api_key = agent.api_key
        system_prompt = agent.system_prompt

        try:
            client = genai.Client(api_key=api_key)
            prompt = f"{system_prompt}\n\nUser Message: {user_text}"

            response = client.models.generate_content(
                model=agent.model_name,
                contents=prompt
            )
            ai_reply = response.text

            env_as_bot = self.with_user(bot_user)
            new_message = env_as_bot.message_post(
                body=ai_reply,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

            Store(new_message).bus_send()
        except Exception as e:
            _logger.error(f"AI Agent Error: {e}")
