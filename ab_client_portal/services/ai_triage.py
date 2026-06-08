"""AI triage service.

Provider-pluggable. The current provider uses the Anthropic Messages API with
JSON-schema-constrained output. Reads key/model from ir.config_parameter; if the
key is missing or the SDK is not installed, the call is a silent no-op so the
submit flow continues uninterrupted.
"""
import json
import logging
from markupsafe import Markup

from odoo import _
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'claude-opus-4-8'
MAX_TOKENS = 1024

TRIAGE_SCHEMA = {
    'type': 'object',
    'properties': {
        'summary': {'type': 'string'},
        'request_type': {
            'type': 'string',
            'enum': ['bug', 'feature', 'integration', 'model_change'],
        },
        'estimate_hours': {'type': 'number'},
        'acceptance_criteria': {'type': 'string'},
        'affected_module': {'type': 'string'},
        'missing_info': {'type': 'array', 'items': {'type': 'string'}},
    },
    'required': [
        'summary', 'request_type', 'estimate_hours',
        'acceptance_criteria', 'affected_module', 'missing_info',
    ],
    'additionalProperties': False,
}

SYSTEM_PROMPT = (
    "You are an Odoo customisation triage assistant for the Agentic Brain agency. "
    "Given a client's change request, produce structured triage output for the dev "
    "team: a 1-3 sentence summary, the most likely request_type, a rough "
    "estimate_hours, a cleaned-up acceptance_criteria (markdown bullets), a guess "
    "at affected_module, and a list of any missing_info items the team should "
    "ask about. Be concise and concrete; do not invent details."
)


def _get_config(env):
    Param = env['ir.config_parameter'].sudo()
    api_key = Param.get_param('ab_client_portal.ai_key', '').strip()
    model = Param.get_param('ab_client_portal.ai_model', DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return api_key, model


def _build_user_message(task):
    description = html2plaintext(task.description or '') if task.description else ''
    criteria = html2plaintext(task.acceptance_criteria or '') if task.acceptance_criteria else ''
    return (
        f"Title: {task.name or ''}\n"
        f"Request type (client-provided): {task.request_type or 'unspecified'}\n"
        f"Client priority: {task.client_priority or 'normal'}\n"
        f"Affected module (client-provided): {task.affected_module or 'unspecified'}\n"
        f"\nDescription:\n{description or '(none)'}\n"
        f"\nAcceptance criteria (client-provided):\n{criteria or '(none)'}\n"
    )


def _call_anthropic(api_key, model, user_message):
    try:
        import anthropic
    except ImportError:
        _logger.info("ab_client_portal: anthropic SDK not installed; skipping AI triage.")
        return None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            thinking={'type': 'disabled'},
            system=SYSTEM_PROMPT,
            output_config={'format': {'type': 'json_schema', 'schema': TRIAGE_SCHEMA}},
            messages=[{'role': 'user', 'content': user_message}],
        )
    except anthropic.AuthenticationError:
        _logger.warning("ab_client_portal: Anthropic auth failed; check ab_client_portal.ai_key.")
        return None
    except Exception:
        _logger.exception("ab_client_portal: Anthropic API call failed.")
        return None
    try:
        text = next(b.text for b in resp.content if getattr(b, 'type', None) == 'text')
        return json.loads(text)
    except (StopIteration, ValueError, json.JSONDecodeError):
        _logger.exception("ab_client_portal: failed to parse Anthropic response.")
        return None


def _format_note(data):
    missing = data.get('missing_info') or []
    missing_html = (
        '<ul>' + ''.join(f'<li>{m}</li>' for m in missing) + '</ul>'
        if missing else '<p><em>None flagged.</em></p>'
    )
    return Markup(
        '<div>'
        '<p><strong>Summary:</strong> {summary}</p>'
        '<p><strong>Suggested type:</strong> {req_type}</p>'
        '<p><strong>Estimate:</strong> ~{hours} hours</p>'
        '<p><strong>Affected module:</strong> {module}</p>'
        '<p><strong>Acceptance criteria (cleaned):</strong></p>'
        '<div>{criteria}</div>'
        '<p><strong>Missing info:</strong></p>'
        '{missing}'
        '</div>'
    ).format(
        summary=data.get('summary', ''),
        req_type=data.get('request_type', ''),
        hours=data.get('estimate_hours', 0),
        module=data.get('affected_module', ''),
        criteria=data.get('acceptance_criteria', ''),
        missing=Markup(missing_html),
    )


def _fill_empty_fields(task, data):
    """Fill structured fields only when empty — never overwrite client input."""
    updates = {}
    if not task.request_type and data.get('request_type'):
        updates['request_type'] = data['request_type']
    if not task.affected_module and data.get('affected_module'):
        updates['affected_module'] = data['affected_module']
    if not task.estimate_hours and data.get('estimate_hours'):
        updates['estimate_hours'] = float(data['estimate_hours'])
    if not task.acceptance_criteria and data.get('acceptance_criteria'):
        updates['acceptance_criteria'] = Markup(
            f"<div>{data['acceptance_criteria']}</div>"
        )
    if updates:
        task.write(updates)


def run_triage(task):
    """Entry point. Always returns silently — never raises."""
    api_key, model = _get_config(task.env)
    if not api_key:
        _logger.info("ab_client_portal: no AI key configured; skipping triage.")
        return
    user_message = _build_user_message(task)
    data = _call_anthropic(api_key, model, user_message)
    if not data:
        return
    note = _format_note(data)
    task.write({'ai_triage_note': note})
    _fill_empty_fields(task, data)
    task.message_post(
        body=note,
        message_type='comment',
        subtype_xmlid='mail.mt_comment',
        subject=_("AI triage"),
    )
