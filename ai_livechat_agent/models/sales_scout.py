from odoo import models, fields, api
from odoo.tools import html2plaintext
from google import genai
import logging

_logger = logging.getLogger(__name__)

class SalesScoutInbox(models.Model):
    _name = 'ai.sales.scout'
    _description = 'AI Sales Scout Email Log'
    _inherit = ['mail.thread']

    name = fields.Char(string="Email Subject")

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ This function runs automatically every time Odoo fetches a new email from Gmail """

        # 1. Create a log record of the email
        custom_values = custom_values or {}
        custom_values['name'] = msg_dict.get('subject', 'No Subject')
        scout_log = super(SalesScoutInbox, self).message_new(msg_dict, custom_values)

        # 2. Find our active Scout Agent
        agent = self.env['ai.agent'].sudo().search([('agent_type', '=', 'scout'), ('active', '=', True)], limit=1)
        if not agent:
            _logger.warning("No active Sales Scout agent found.")
            return scout_log

        # 3. Clean the email text
        subject = msg_dict.get('subject', '')
        body_text = html2plaintext(msg_dict.get('body', ''))

        try:
            client = genai.Client(api_key=agent.api_key)

            # 4. Ask Gemini to evaluate the Upwork Job
            eval_prompt = f"""
            {agent.system_prompt}

            Evaluate this Upwork job. If it is a good fit for our company, reply with EXACTLY 'YES' followed by a score from 1-10.
            If it is not a good fit, reply with EXACTLY 'NO'.

            Job Title: {subject}
            Job Description: {body_text}
            """
            response = client.models.generate_content(model=agent.model_name, contents=eval_prompt)
            ai_evaluation = response.text.strip().upper()

            # 5. If it's a good fit, create the Opportunity in the CRM!
            if ai_evaluation.startswith('YES'):
                is_important = '9' in ai_evaluation or '10' in ai_evaluation

                lead = self.env['crm.lead'].create({
                    'name': f"Scouted: {subject}",
                    'description': body_text,
                    'user_id': agent.user_id.id,
                    'type': 'opportunity', # Put it directly in the pipeline
                    'priority': '3' if is_important else '1',
                })

                # 6. Generate the Proposal using past Odoo tasks
                self._generate_proposal(client, agent, lead, body_text)

                # Notify the team if it's a 9/10 or 10/10 job
                if is_important:
                    lead.message_post(
                        body=f"🚨 **High Priority Lead Scouted!** AI Score: {ai_evaluation}. A draft proposal has been generated.",
                        subtype_xmlid='mail.mt_note'
                    )

        except Exception as e:
            _logger.error(f"AI Scout Error processing email: {e}")

        return scout_log

    def _generate_proposal(self, client, agent, lead, job_description):
        """Reads completed tasks from Odoo Projects to write a customized proposal"""

        # Fetch 5 recently completed tasks for context
        completed_tasks = self.env['project.task'].search([('state', 'in', ['1_done', 'done'])], limit=5)
        portfolio_text = "\n".join([f"- {task.name}" for task in completed_tasks])

        proposal_prompt = f"""
        {agent.proposal_prompt}

        Based on our completed projects below, write a professional proposal for this job.

        Our Portfolio:
        {portfolio_text}

        The Job:
        {job_description}
        """
        response = client.models.generate_content(model=agent.model_name, contents=proposal_prompt)

        # Save the proposal inside the CRM Lead
        lead.message_post(body=f"**🤖 AI Generated Draft Proposal:**\n\n{response.text}", subtype_xmlid='mail.mt_note')
