from odoo import http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


REQUEST_TYPES = [
    ('bug', 'Bug'),
    ('feature', 'Feature'),
    ('integration', 'Integration'),
    ('model_change', 'Model Change'),
]
CLIENT_PRIORITIES = [('low', 'Low'), ('normal', 'Normal'), ('high', 'High')]


class ClientPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'request_count' in counters:
            values['request_count'] = (
                request.env['project.task'].search_count(self._request_base_domain())
                if request.env['project.task'].has_access('read') else 0
            )
        return values

    def _request_base_domain(self):
        partner = request.env.user.partner_id.commercial_partner_id
        return [
            ('project_id.privacy_visibility', '=', 'portal'),
            ('project_id.partner_id', 'child_of', [partner.id]),
        ]

    def _user_projects(self):
        """Portal projects where the current user's commercial partner is the customer."""
        partner = request.env.user.partner_id.commercial_partner_id
        return request.env['project.project'].sudo().search([
            ('privacy_visibility', '=', 'portal'),
            ('partner_id', 'child_of', [partner.id]),
        ])

    def _get_task_or_redirect(self, task_id, access_token=None):
        try:
            return self._document_check_access('project.task', int(task_id), access_token)
        except (AccessError, MissingError):
            return None

    @http.route(['/my/requests', '/my/requests/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_requests(self, page=1, **kw):
        Task = request.env['project.task']
        domain = self._request_base_domain()
        total = Task.search_count(domain)
        pager = portal_pager(
            url='/my/requests',
            total=total,
            page=page,
            step=20,
        )
        tasks = Task.search(domain, limit=20, offset=pager['offset'], order='create_date desc')
        values = self._prepare_portal_layout_values()
        values.update({
            'tasks': tasks,
            'pager': pager,
            'page_name': 'requests',
            'default_url': '/my/requests',
        })
        return request.render('ab_client_portal.portal_my_requests', values)

    @http.route(['/my/requests/new'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_request_new(self, **post):
        projects = self._user_projects()
        if not projects:
            return request.render('ab_client_portal.portal_request_no_project', {})
        if request.httprequest.method == 'POST':
            project_id = int(post.get('project_id') or projects[:1].id)
            if project_id not in projects.ids:
                raise AccessError(_("Invalid project selection."))
            draft_stage = request.env.ref('ab_client_portal.stage_draft', raise_if_not_found=False)
            vals = {
                'project_id': project_id,
                'name': (post.get('name') or '').strip() or _('Untitled request'),
                'description': post.get('description') or '',
                'request_type': post.get('request_type') or False,
                'client_priority': post.get('client_priority') or 'normal',
                'affected_module': (post.get('affected_module') or '').strip(),
                'acceptance_criteria': post.get('acceptance_criteria') or '',
                'partner_id': request.env.user.partner_id.id,
            }
            if draft_stage:
                vals['stage_id'] = draft_stage.id
            task = request.env['project.task'].sudo().create(vals)
            task.message_subscribe(partner_ids=[request.env.user.partner_id.id])
            return request.redirect('/my/requests/%s' % task.id)
        return request.render('ab_client_portal.portal_request_form', {
            'task': None,
            'projects': projects,
            'request_types': REQUEST_TYPES,
            'client_priorities': CLIENT_PRIORITIES,
            'page_name': 'requests',
        })

    @http.route(['/my/requests/<int:task_id>'], type='http', auth='public', website=True)
    def portal_request_view(self, task_id, access_token=None, **kw):
        task_sudo = self._get_task_or_redirect(task_id, access_token)
        if task_sudo is None:
            return request.redirect('/my')
        return request.render('ab_client_portal.portal_request_form', {
            'task': task_sudo,
            'projects': self._user_projects(),
            'request_types': REQUEST_TYPES,
            'client_priorities': CLIENT_PRIORITIES,
            'page_name': 'requests',
        })

    @http.route(['/my/requests/<int:task_id>/edit'], type='http', auth='user', website=True, methods=['POST'])
    def portal_request_edit(self, task_id, **post):
        task_sudo = self._get_task_or_redirect(task_id)
        if task_sudo is None:
            return request.redirect('/my')
        if not task_sudo.is_client_editable:
            raise UserError(_("This request is no longer editable."))
        task_sudo.write({
            'name': (post.get('name') or task_sudo.name).strip() or task_sudo.name,
            'description': post.get('description') or task_sudo.description,
            'request_type': post.get('request_type') or task_sudo.request_type,
            'client_priority': post.get('client_priority') or task_sudo.client_priority,
            'affected_module': (post.get('affected_module') or '').strip(),
            'acceptance_criteria': post.get('acceptance_criteria') or task_sudo.acceptance_criteria,
        })
        return request.redirect('/my/requests/%s' % task_sudo.id)

    @http.route(['/my/requests/<int:task_id>/submit'], type='http', auth='user', website=True, methods=['POST'])
    def portal_request_submit(self, task_id, **post):
        task_sudo = self._get_task_or_redirect(task_id)
        if task_sudo is None:
            return request.redirect('/my')
        partner_id = request.env.user.partner_id.commercial_partner_id.id
        task_sudo.with_context(portal_partner_id=partner_id).action_client_submit()
        return request.redirect('/my/requests/%s' % task_sudo.id)
