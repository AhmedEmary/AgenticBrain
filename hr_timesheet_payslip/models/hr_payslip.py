from odoo import _, models
from odoo.exceptions import UserError

INPUT_CODE = "TS_HOURS"
PARAM_VALIDATED_ONLY = "hr_timesheet_payslip.validated_only"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _ts_get_input_type(self):
        return self.env.ref(
            "hr_timesheet_payslip.input_type_ts_hours",
            raise_if_not_found=False,
        )

    def _ts_validated_only(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(PARAM_VALIDATED_ONLY, "False")
            == "True"
        )

    def _ts_timesheet_domain(self):
        self.ensure_one()
        domain = [
            ("employee_id", "=", self.employee_id.id),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("project_id", "!=", False),
        ]
        AAL = self.env["account.analytic.line"]
        if self._ts_validated_only() and "validated" in AAL._fields:
            domain.append(("validated", "=", True))
        return domain

    def _ts_sum_hours(self):
        self.ensure_one()
        if not self.employee_id or not self.date_from or not self.date_to:
            return 0.0
        AAL = self.env["account.analytic.line"].sudo()
        groups = AAL.read_group(
            domain=self._ts_timesheet_domain(),
            fields=["unit_amount:sum"],
            groupby=[],
        )
        return groups[0]["unit_amount"] if groups else 0.0

    def _ts_sync_input_line(self):
        """Replace any existing TS_HOURS input on this payslip with a fresh
        line whose amount equals the timesheet hours for the period."""
        self.ensure_one()
        input_type = self._ts_get_input_type()
        if not input_type:
            raise UserError(
                _(
                    "Payslip input type 'TS_HOURS' is missing. "
                    "Reinstall the hr_timesheet_payslip module or load its data."
                )
            )
        hours = self._ts_sum_hours()
        existing = self.input_line_ids.filtered(lambda l: l.code == INPUT_CODE)
        if existing:
            existing.unlink()
        # Don't add a zero line; the rule's condition_python handles the missing case.
        if hours <= 0:
            return
        self.env["hr.payslip.input"].create(
            {
                "payslip_id": self.id,
                "input_type_id": input_type.id,
                "amount": hours,
                "name": _("Timesheet hours (auto)"),
                "sequence": 10,
            }
        )

    def compute_sheet(self):
        # Refresh TS_HOURS for every draft payslip BEFORE the rules run.
        for payslip in self.filtered(lambda p: p.state == "draft"):
            payslip._ts_sync_input_line()
        return super().compute_sheet()
