# hr_timesheet_payslip — Timesheet-driven Payslips (Odoo 19)

Bridges Timesheets and Payroll for **hourly contracts**. Odoo's payslip
engine reads `hr.work.entry`, not timesheets — this module sums the
employee's logged timesheet hours for the payslip period and injects
them as a `TS_HOURS` Other Input on the payslip. A shipped salary rule
then prices those hours against `hr.version.hourly_wage`.

The number is visible and editable on the payslip form **before** you
validate, so HR can override if needed.

> Odoo 19 note: the wage configuration that lived on `hr.contract` in
> earlier versions now lives on `hr.version` (`wage_type`,
> `hourly_wage`, …). The payslip references it as `version_id`, and in
> salary-rule Python code the localdict key is `version` (not
> `contract`). This module is written against the 19.0 source.

---

## Section A — The custom module (self-hosted)

### Layout

```
hr_timesheet_payslip/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── hr_payslip.py            # overrides compute_sheet
│   └── res_config_settings.py   # "validated-only" toggle
├── data/
│   ├── hr_payslip_input_type_data.xml   # TS_HOURS input type + struct link
│   └── hr_salary_rule_data.xml          # TSPAY salary rule
├── views/
│   └── res_config_settings_views.xml
├── security/
│   └── ir.model.access.csv      # stub — no new models, no ACL needed
└── README.md
```

### How it works

1. **`hr.payslip.compute_sheet` override** — before the rule engine runs,
   we recompute the timesheet hours for each draft payslip, delete any
   stale `TS_HOURS` input line, and create a fresh one whose `amount` is
   the period's total hours.
2. **Timesheet domain** (per-employee, per-period, project-bound):
   ```python
   [
       ('employee_id', '=', self.employee_id.id),
       ('date',       '>=', self.date_from),
       ('date',       '<=', self.date_to),
       ('project_id', '!=', False),
   ]
   ```
   When the "validated-only" toggle is on **and** the `validated` field
   exists on `account.analytic.line` (i.e., the `timesheet_grid`
   enterprise module is installed), we add `('validated', '=', True)`.
   On databases without `timesheet_grid` the toggle silently no-ops,
   because the field doesn't exist.
3. **Salary rule `TSPAY`** (in `data/hr_salary_rule_data.xml`):
   ```python
   # condition_python
   result = ('TS_HOURS' in inputs) and (inputs['TS_HOURS'].amount > 0) \
            and version.wage_type == 'hourly'

   # amount_python_compute
   result_qty  = inputs['TS_HOURS'].amount
   result      = version.hourly_wage
   result_rate = 100.0
   ```
   Odoo 19 stores the line amount as
   `result * result_qty * result_rate / 100`, so hours appear in
   `result_qty` and rate in `result` exactly once. **Do not** also
   multiply hours into `result` — that double-counts.

### Install

1. Drop the module into your custom addons path (you already have:
   `custom_addons/hr_timesheet_payslip/`).
2. Restart Odoo with `--update=base` or just restart, then go to
   **Apps → Update Apps List**.
3. Search for *Timesheet-driven Payslip* and click **Install**.

### Configure

- **Payroll → Configuration → Settings → Timesheet-driven Payslips**:
  toggle *Only validated timesheets count toward payslip*.
- Make sure each employee has an **hr.version** (i.e., a contract record
  in Odoo 19 terms) with:
  - `wage_type` = **Hourly**
  - `hourly_wage` set
  - `structure_type_id` whose default structure either *is*
    `hr_payroll.default_structure` (the shipped rule attaches there) or
    has the `TSPAY` rule and the `TS_HOURS` input type added to it.
- **For custom payroll structures** (most production setups): open
  **Payroll → Configuration → Salary Structures**, pick your structure,
  then:
  - Add **Timesheet Hours** to the *Other Input Line* list.
  - Duplicate the *Timesheet Pay (Hourly)* salary rule and reassign its
    *Salary Structure* to yours.

---

## Section B — SaaS-safe (Odoo Online, no module install)

Use this when you can't install Python files (Odoo Online). It does the
same thing entirely from the UI by **reading timesheets at rule
evaluation time** via `payslip.env`.

### B1. Add the input type (UI)

**Payroll → Configuration → Other Input Types → New**
- Description: `Timesheet Hours`
- Code: `TS_HOURS`
- Is quantity?: ✅

Then on your salary structure (**Payroll → Configuration → Salary
Structures**), add `Timesheet Hours` to *Other Input Line*. This makes
the input visible/editable on the payslip form for the manual fallback.

### B2. Create the salary rule (UI)

**Payroll → Configuration → Rules → New**

- Name: `Timesheet Pay (Hourly)`
- Code: `TSPAY`
- Salary Structure: *your structure*
- Category: `Basic`
- Sequence: `5`
- Condition Based on: **Python Expression**
  ```python
  result = version.wage_type == 'hourly' and bool(version.hourly_wage)
  ```
- Amount Type: **Python Code**
  ```python
  # SaaS-safe pricing rule — reads timesheets directly at compute time.
  # Falls back to a manual 'TS_HOURS' Other Input if env access is sandboxed.
  hours = 0.0
  try:
      AAL = payslip.env['account.analytic.line'].sudo()
      domain = [
          ('employee_id', '=', employee.id),
          ('date',       '>=', payslip.date_from),
          ('date',       '<=', payslip.date_to),
          ('project_id', '!=', False),
      ]
      # Only count validated timesheets if the field exists in this DB.
      if 'validated' in AAL._fields:
          domain.append(('validated', '=', True))
      groups = AAL.read_group(domain, ['unit_amount:sum'], [])
      hours = groups[0]['unit_amount'] if groups else 0.0
  except Exception:
      hours = 0.0

  # Manual override / fallback: if HR typed a value into the
  # 'TS_HOURS' Other Input on the payslip, prefer that.
  if 'TS_HOURS' in inputs and inputs['TS_HOURS'].amount:
      hours = inputs['TS_HOURS'].amount

  result_qty  = hours
  result      = version.hourly_wage
  result_rate = 100.0
  ```

### B3. Manual "Other Input" fallback

If `payslip.env` is sandboxed out on your Odoo Online instance (it
usually isn't, but worth knowing), the same rule still works — just
enter the hours by hand on each payslip:

1. Open the draft payslip → **Other Inputs** tab → add a line:
   - Description: `Timesheet hours`
   - Type: `Timesheet Hours` (the `TS_HOURS` type you created in B1)
   - Amount: total hours for the period.
2. Hit **Compute Sheet**.

The rule above already prefers the manually-entered `TS_HOURS` over the
timesheet sum, so the override path is automatic.

---

## Generating, computing, confirming, and emailing the payslip

Identical for both A and B.

### Single payslip

1. **Payroll → Payslips → All Payslips → New**.
2. Pick the employee, set *Date From* / *Date To*. The *Salary Structure*
   auto-fills from the employee's version; *Contract* (the
   `version_id`) also auto-fills.
3. Click **Compute Sheet**. You should see:
   - In *Other Inputs*: a `TS_HOURS` line with the period's hours.
   - In *Salary Computation*: a `TSPAY` line = `hourly_wage × hours`.
4. (Optional) Tweak the `TS_HOURS` amount and **Compute Sheet** again to
   re-price.
5. Click **Mark as Done** (or **Confirm**) to lock the slip.
6. **Send By Email** in the chatter (or use the *Send* button on the
   slip): pick the *Payroll: Send Payslip by email* template. Odoo
   attaches the rendered payslip PDF and emails it to the employee's
   work email.

> The mail template ships with `hr_payroll` as
> `hr_payroll.mail_template_new_payslip` (Payroll → Configuration →
> Email Templates). Edit the body/subject there if you want a custom
> wording.

### Batch (hr.payslip.run)

1. **Payroll → Payslips → Batches → New**.
2. Set the *Period* (same `date_from`/`date_to`).
3. Click **Generate Payslips**, pick the employees (and structure if
   prompted) → **Generate**.
4. With the batch open, click **Compute Sheets** — each child payslip's
   `compute_sheet()` runs and our override injects each employee's
   `TS_HOURS`.
5. Review individually, then **Validate** the batch to confirm all
   slips at once.
6. Click **Send Payslips by Email** on the batch to mass-mail PDFs to
   every employee on it.

---

## Sanity checks before you trust the numbers

- **One multiplication only.** The shipped rule sets
  `result = hourly_wage` and `result_qty = hours`. If you tweak the
  rule, remember Odoo multiplies them for you — don't multiply hours
  into `result` again.
- **Project filter.** Internal/HR analytic lines without a project are
  excluded (`project_id != False`), matching the spec.
- **Validated-only toggle.** No-ops on Odoo Community / databases
  without `timesheet_grid`; the override probes
  `'validated' in account.analytic.line._fields` before adding the
  domain term.
- **Re-compute is idempotent.** Each `compute_sheet()` deletes any
  prior `TS_HOURS` input line on the slip and recreates it from scratch.
- **Non-hourly versions are skipped.** `condition_python` checks
  `version.wage_type == 'hourly'`, so the rule prices nothing on a
  monthly contract even if `TS_HOURS` is present.
