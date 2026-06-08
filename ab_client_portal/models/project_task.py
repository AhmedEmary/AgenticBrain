import logging
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

STAGE_XMLID_TO_CLIENT_STATUS = (
    ('ab_client_portal.stage_draft', 'draft'),
    ('ab_client_portal.stage_submitted', 'submitted'),
    ('ab_client_portal.stage_under_review', 'under_review'),
    ('ab_client_portal.stage_approved', 'approved'),
    ('ab_client_portal.stage_in_progress', 'in_progress'),
    ('ab_client_portal.stage_delivered', 'delivered'),
)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    client_status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('in_progress', 'In Progress'),
            ('delivered', 'Delivered'),
        ],
        string='Client Status',
        compute='_compute_client_status',
        store=True,
        tracking=True,
        help="Status shown to the client in the portal. Derived from the internal stage.",
    )
    is_client_editable = fields.Boolean(
        string='Editable by Client',
        compute='_compute_is_client_editable',
        help="True while the request is in Draft and the client may edit it.",
    )
    request_type = fields.Selection(
        [
            ('bug', 'Bug'),
            ('feature', 'Feature'),
            ('integration', 'Integration'),
            ('model_change', 'Model Change'),
        ],
        string='Request Type',
    )
    acceptance_criteria = fields.Html(string='Acceptance Criteria')
    affected_module = fields.Char(string='Affected Module')
    client_priority = fields.Selection(
        [('low', 'Low'), ('normal', 'Normal'), ('high', 'High')],
        string='Client Priority',
        default='normal',
    )
    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, tracking=True, copy=False,
    )
    approved_date = fields.Datetime(string='Approved On', readonly=True, copy=False)
    estimate_hours = fields.Float(string='Estimate (hours)', tracking=True)
    ai_triage_note = fields.Html(string='AI Triage Note', readonly=True, copy=False)

    def _stage_to_client_status_map(self):
        """Resolve stage XML-IDs → client_status keys once per call."""
        result = {}
        for xmlid, status in STAGE_XMLID_TO_CLIENT_STATUS:
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage:
                result[stage.id] = status
        return result

    @api.depends('stage_id')
    def _compute_client_status(self):
        mapping = self._stage_to_client_status_map()
        for task in self:
            task.client_status = mapping.get(task.stage_id.id, 'draft')

    @api.depends('client_status')
    def _compute_is_client_editable(self):
        for task in self:
            task.is_client_editable = task.client_status == 'draft'

    def _assert_portal_owner(self):
        """Guard: the current portal user's commercial partner is the project's customer."""
        self.ensure_one()
        partner_id = self.env.context.get('portal_partner_id') or self.env.user.partner_id.commercial_partner_id.id
        customer = self.project_id.partner_id.commercial_partner_id
        if not customer or customer.id != partner_id:
            raise AccessError(_("You do not have access to this request."))

    def action_client_submit(self):
        """Portal-callable: lock the draft, ack the client, queue triage."""
        for task in self:
            if not task.is_client_editable:
                raise UserError(_("This request is no longer editable."))
            task._assert_portal_owner()
            stage_submitted = self.env.ref(
                'ab_client_portal.stage_submitted', raise_if_not_found=False,
            )
            if stage_submitted:
                task.sudo().stage_id = stage_submitted
            task._post_submit_acknowledgement()
            task._create_triage_activity()
            task._run_ai_triage()
        return True

    def _post_submit_acknowledgement(self):
        self.ensure_one()
        template = self.env.ref(
            'ab_client_portal.mail_template_request_acknowledgement',
            raise_if_not_found=False,
        )
        if template:
            template.sudo().send_mail(self.id, force_send=False)

    def _create_triage_activity(self):
        self.ensure_one()
        responsible = self.project_id.user_id or self.env.user
        self.sudo().activity_schedule(
            'mail.mail_activity_data_todo',
            summary=_("Triage new client request"),
            note=_("Review the submitted request and approve or send back for clarification."),
            user_id=responsible.id,
        )

    def _run_ai_triage(self):
        """Call the AI triage service. Never raises — submit must not break."""
        self.ensure_one()
        try:
            from ..services.ai_triage import run_triage
            run_triage(self.sudo())
        except Exception:
            _logger.exception("AI triage failed for task %s; continuing.", self.id)

    def action_internal_approve(self):
        """Backend-only Approve. Restricted to project users/managers."""
        if not self.env.user.has_group('project.group_project_user'):
            raise AccessError(_("Only project members can approve client requests."))
        stage_approved = self.env.ref(
            'ab_client_portal.stage_approved', raise_if_not_found=False,
        )
        stage_in_progress = self.env.ref(
            'ab_client_portal.stage_in_progress', raise_if_not_found=False,
        )
        billing_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'ab_client_portal.billing_enabled', 'False',
        ) == 'True'
        for task in self:
            task.check_access('write')
            task.write({
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            target_stage = stage_approved if billing_enabled else stage_in_progress
            if target_stage:
                task.stage_id = target_stage
            task.message_post(
                body=_("Request approved by %(user)s.", user=self.env.user.name),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            if billing_enabled:
                task._generate_billing_quote()
        return True

    def _generate_billing_quote(self):
        """Create a draft sale.order if sale_project is installed. Soft dep."""
        self.ensure_one()
        SaleOrder = self.env.get('sale.order')
        if SaleOrder is None:
            _logger.info(
                "Billing enabled but sale_project is not installed; skipping quote for task %s.",
                self.id,
            )
            return
        if not self.partner_id:
            _logger.info("Task %s has no partner_id; skipping quote.", self.id)
            return
        SaleOrder.sudo().create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
        })
