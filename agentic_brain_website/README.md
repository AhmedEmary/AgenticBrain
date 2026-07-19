# Agentic Brain Website — Odoo module

A modern, animated homepage for **Agentic Brain Solutions** (Odoo ERP + autonomous AI agents).
Framework-free: pure QWeb + CSS + vanilla JS. No external build step.

## What it does
- Replaces the Website homepage (`/`) with the new premium design.
- Uses the design's own nav + footer and automatically **hides Odoo's theme
  header/footer only on the homepage** (scoped via CSS `:has(.ab-wrap)`).
- All other pages (Services, About, Appointment, Contact) keep your existing theme.

## Requirements
- Odoo 16 / 17 / 18 with the **Website** app installed.
- A modern browser (the header/footer hiding uses CSS `:has()`, supported in all
  current browsers — Odoo's backend never renders the frontend so this is fine).

## Install (SSH / server access)
1. Copy the whole `agentic_brain_website/` folder into your Odoo addons path, e.g.:
   ```
   /mnt/extra-addons/agentic_brain_website
   ```
2. Restart Odoo:
   ```
   sudo service odoo restart      # or: ./odoo-bin -c odoo.conf -u agentic_brain_website
   ```
3. In Odoo: **Apps → Update Apps List**, search **Agentic Brain Website**, click **Install**.
4. Open your site's homepage — the new design is live.

## Update after editing
```
./odoo-bin -c odoo.conf -u agentic_brain_website
```
(or bump the version in `__manifest__.py` and use Apps → Upgrade).

## Files
```
agentic_brain_website/
├── __manifest__.py
├── __init__.py
├── views/
│   └── homepage.xml          # QWeb template (inherits website.homepage)
├── static/src/
│   ├── css/style.css         # styles, animations, hover, header/footer hiding
│   ├── js/main.js            # rotating word, scroll reveal, count-up stats
│   └── img/                  # logo + dashboard / agent / workflow mockups
└── preview.html              # standalone local preview (not used by Odoo)
```

## Swapping the mockup images for real screenshots
Replace these files (keep the same names) and upgrade the module:
- `static/src/img/dashboard.png` — hero unified-dashboard image
- `static/src/img/agent.png` — AI agent control-room image
- `static/src/img/workflow.png` — AI + Odoo workflow diagram

## Editing text
All copy lives in `views/homepage.xml`. After editing, upgrade the module
(`-u agentic_brain_website`). You can also make the section editable in the
Website builder later — ask and I'll add `oe_structure` / editable snippets.

## Notes
- Phone, email and links point to your real details and Odoo routes
  (`/contactus`, `/appointment`, `/our-services`, `/about-us`).
- If you prefer to KEEP Odoo's theme header/footer, delete the first CSS rule
  block in `static/src/css/style.css` (the `:has(.ab-wrap)` one).
