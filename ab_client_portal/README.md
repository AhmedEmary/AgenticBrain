# ab_client_portal

Client-facing project portal for Agentic Brain. Clients submit, edit, and track change
requests against a dedicated portal-mode project; the agency reviews, runs AI-assisted
triage, and approves from the standard backend kanban. The client view is decoupled from
internal stage names via a stored `client_status` field.

## Install / upgrade

```bash
# From the workspace root
cd /home/odoo/Desktop/Agentic_Solutions
./odoo/odoo-bin -d <db> -u ab_client_portal \
  --addons-path=odoo/addons,enterprise,custom_addons
```

The first install seeds 6 client-portal stages (`Draft`, `Submitted`, `Under Review`,
`Approved`, `In Progress`, `Delivered`) and two mail templates. No existing projects or
tasks are modified.

### Python dependency

The AI triage step needs the Anthropic SDK:

```bash
pip install anthropic
```

If the SDK is missing, triage is skipped silently and the submit flow still works.

## Configuration (Settings → Technical → Parameters → System Parameters)

| Key | Default | Notes |
| --- | --- | --- |
| `ab_client_portal.ai_key` | *(unset)* | Anthropic API key. If empty, AI triage is skipped silently. |
| `ab_client_portal.ai_model` | `claude-opus-4-8` | Anthropic model. Common alternatives: `claude-sonnet-4-6` ($3/$15 per 1M tok) or `claude-haiku-4-5` ($1/$5). Opus 4.8 is $5/$25 and the default. |
| `ab_client_portal.billing_enabled` | `False` | When `True` and `sale_project` is installed, the Approve action creates a draft `sale.order`. Otherwise this is a no-op. |

### Enabling billing

The module does **not** depend on `sale_project` / `sale_timesheet` directly, so it
installs cleanly without them. To turn on the quote-generation flow:

1. `pip install` whatever is needed and install the `sale_project` module:
   `./odoo-bin -d <db> -u sale_project`.
2. Set `ab_client_portal.billing_enabled = True`.

If billing is enabled but `sale_project` is not installed, the approval still works —
the quote step is skipped with an info log.

## Setting up a project for a client

For each client, create a project the standard way and:

1. Set **Visibility** to **Visible by following customers** (`privacy_visibility = 'portal'`).
2. Set the **Customer** to the client's partner record.
3. Attach the six client-portal stages (`Settings → Stages` on the project), or call
   `project.action_setup_as_client_portal()` from a server action.
4. Add the portal user(s) of the client as followers.

Client A's portal users never see Client B's project — enforced by Odoo's native portal
rule plus an extra `ir.rule` defined in this module (`security/ab_client_portal_security.xml`)
that requires the task's `partner_id` or `message_partner_ids` to be inside the user's
commercial org.

## Manual test script

```text
PRECONDITIONS
- Two portal partners: Client A and Client B, each with at least one portal user.
- Two portal-visibility projects: "Client A — Requests" and "Client B — Requests",
  each with the six ab_client_portal stages attached and the matching client partner
  added as follower.
- Optional: set ab_client_portal.ai_key for the AI-triage assertions.

1. Log in as Client A's portal user.
   → /my shows a "My Requests" tile (count starts at 0).
2. /my/requests → "New Request".
   → Project dropdown lists only "Client A — Requests".
   → Fill title, type=feature, priority=normal, acceptance criteria, description.
   → "Create Draft" → redirected to /my/requests/<id> in editable mode.
3. On the draft, click "Submit Request".
   → Status badge becomes "Submitted".
   → All fields are read-only.
   → If AI key configured: AI Triage Note block renders with summary + suggestions,
     a corresponding chatter message is posted, and any fields the client left blank
     (request_type / affected_module / estimate_hours / acceptance_criteria) are
     auto-filled. Existing client values are never overwritten.
   → If no AI key: no traceback, info log "no AI key configured; skipping triage".
   → A mail.activity is created on the task, assigned to the project's user.
4. Log in as an internal Project User. Open the submitted task in the backend.
   → Form shows a "Client Portal" notebook tab with all new fields.
   → Header "Approve" button is visible.
   → Click "Approve".
   → approved_by and approved_date are stamped.
   → Stage moves to "Approved" (billing on) or "In Progress" (billing off).
   → A chatter message records the approval.
5. As Client A's portal user, revisit /my/requests/<id>.
   → Status badge updated.
   → Client received a status-change notification (via tracking on client_status).
6. Multi-client isolation:
   → Log in as Client B's portal user.
   → /my/requests lists 0 items.
   → Visit /my/requests/<A's task id> directly → redirected to /my.
7. AI-disabled path:
   → Clear ab_client_portal.ai_key.
   → Create + submit another draft.
   → Submit succeeds, no AI note, no traceback in the log.
```

## File map

```
ab_client_portal/
├── controllers/portal.py                    CustomerPortal + /my/requests routes
├── data/ir_config_parameter_data.xml        ai_model + billing_enabled defaults
├── data/mail_template_data.xml              ack + status-change templates
├── data/project_task_type_data.xml          6 client-portal stages (XML-IDs)
├── models/project_task.py                   fields, computes, submit/approve actions
├── models/project_project.py                action_setup_as_client_portal helper
├── security/ir.model.access.csv             (no new models)
├── security/ab_client_portal_security.xml   portal isolation safety-net ir.rule
├── services/ai_triage.py                    Anthropic Messages API call, degrades silently
├── views/portal_templates.xml               QWeb: home tile + list + form + badge
├── views/project_task_views.xml             backend form/list inheritance + menu
└── views/project_task_actions.xml           bulk-approve server action
```
