from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hr_ts_payslip_validated_only = fields.Boolean(
        string="Only validated timesheets count toward payslip",
        config_parameter="hr_timesheet_payslip.validated_only",
        help=(
            "When enabled, only timesheet lines whose 'validated' flag is True "
            "are summed into the TS_HOURS payslip input. Requires the "
            "Timesheets Validation feature (timesheet_grid); the toggle has "
            "no effect on databases where the 'validated' field is absent."
        ),
    )
