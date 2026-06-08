from odoo import models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def action_setup_as_client_portal(self):
        """Convenience: flip a project to portal visibility and attach the
        6 client-portal stages. Manager-callable from a server action."""
        stage_xmlids = (
            'ab_client_portal.stage_draft',
            'ab_client_portal.stage_submitted',
            'ab_client_portal.stage_under_review',
            'ab_client_portal.stage_approved',
            'ab_client_portal.stage_in_progress',
            'ab_client_portal.stage_delivered',
        )
        stages = self.env['project.task.type']
        for xmlid in stage_xmlids:
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage:
                stages |= stage
        for project in self:
            project.privacy_visibility = 'portal'
            if stages:
                project.write({'type_ids': [(4, s.id) for s in stages]})
        return True
