from odoo import models

class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_available_operators_by_livechat_channel(self, users=None):
        # 1. Call the original Odoo 19 logic to get currently online humans
        operators_by_channel = super()._get_available_operators_by_livechat_channel(users=users)

        for channel in self:
            # 2. Search for the "Aisha AI" user within this specific channel's agents
            aisha = channel.user_ids.sudo().filtered(lambda u: u.name == 'Support-ai')

            # 3. Force Aisha into the RecordSet of available operators for this channel
            if aisha:
                # the |= operator adds the user to the RecordSet without creating duplicates
                operators_by_channel[channel] |= aisha

        return operators_by_channel
