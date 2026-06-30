{
    "name": "Timesheet-driven Payslip (Hourly Contracts)",
    "version": "19.0.1.0.0",
    "summary": "Compute payslips from logged timesheet hours for employees on hourly contracts.",
    "description": """
Bridges Odoo Timesheets and Payroll: at payslip compute time, sums the
employee's logged timesheet hours (account.analytic.line) for the payslip
period and injects them as a 'TS_HOURS' Other Input on the payslip. A
salary rule then prices those hours against the employee's hourly_wage
(on hr.version, the Odoo 19 contract record).
""",
    "author": "Custom",
    "license": "LGPL-3",
    "category": "Human Resources/Payroll",
    "depends": [
        "hr_payroll",
        "hr_timesheet",
        "project",
    ],
    "data": [
        "data/hr_payslip_input_type_data.xml",
        "data/hr_salary_rule_data.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
