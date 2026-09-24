# Shipment Management for Odoo 19

A custom Odoo addon for registering shipments, preparing cargo, recording delivery progress and printing a shipment order for the driver. It brings the request, cargo lines and change history into one operational screen.

**Stack:** Python, Odoo ORM, PostgreSQL, XML/QWeb and JavaScript. The [manifest](__manifest__.py) declares Odoo **19.0**, version **19.0.6.1.0**, dependencies on `base` and `mail`, and the **LGPL-3** license.

## What it does

- Saves incomplete requests as drafts, then checks customer, route and dates at confirmation. References are assigned on confirmation using the shipment type and a sequence.
- Provides workflow actions for **Draft → Preparing → With Courier → On The Way → Delivered**, plus cancellation and reset to draft. Courier handover requires cargo.
- Calculates shipment weight and volume from quantities and per-unit cargo values. Cargo edits are restricted to draft and preparation stages.
- Gives shipment users access to requests and cargo, while managers also maintain the shipment-type catalog.
- Includes list, form, search and grouped kanban views; Odoo chatter tracks selected field and status changes.
- Generates a QWeb shipment-order PDF with a Code128 barcode, cargo totals and signature fields. A scoped JavaScript form patch confirms discarding unsaved changes.

## Code to explore

| Area | Entry point |
| --- | --- |
| Lifecycle actions, validation, references and totals | [models/shipment_request.py](models/shipment_request.py) |
| Cargo calculations and edit rules | [models/shipment_item.py](models/shipment_item.py) |
| Type catalog and access permissions | [models/shipment_type.py](models/shipment_type.py), [security/ir.model.access.csv](security/ir.model.access.csv) |
| Report layout and form behavior | [report/shipment_report_templates.xml](report/shipment_report_templates.xml), [static/src/form_discard_confirmation.js](static/src/form_discard_confirmation.js) |

The three custom models are `shipment.request`, `shipment.item` and `shipment.type`. Customers reuse Odoo's `res.partner`; change tracking reuses `mail.thread`.

## Install in a development instance

Use a working **Odoo 19** installation with PostgreSQL and the standard report-rendering dependencies. This repository contains the addon, not an Odoo server or Docker Compose stack. See the official [Odoo 19 source installation guide](https://www.odoo.com/documentation/19.0/administration/on_premise/source.html) for the host setup.

1. Clone the repository into your custom addons directory with the technical module name **`shipment_management`**:

   ```bash
   git clone https://github.com/cs5067/odoo19-shipment-management.git /path/to/custom-addons/shipment_management
   ```

2. Add `/path/to/custom-addons` to Odoo's `addons_path`, preserving the existing addon paths. The parent directory belongs in this setting; the clone's final directory name must be `shipment_management` because the report and asset references use it.
3. Restart Odoo, enable developer mode, update the Apps list and install **Shipment Management** in a development database.
4. Under **Settings → Users**, assign the **Shipment Management / Manager** role to the user trying the full workflow. Refresh the browser, then open **Shipments**.

## Try the workflow

Create an Express shipment type and a test customer. Save a partial shipment draft, complete its route and dates, and confirm it. Add a cargo line with positive quantity, unit weight and unit volume. Move it through courier handover, transit and delivery; inspect the totals and chatter, then print **Shipment Order**. A second draft can be used to check cancellation and reset.

## Scope and verification

This is a focused shipment-management addon. Carrier APIs, fleet management, pricing, accounting integration and dedicated multi-company rules are not included. Routes are free text and there is no assigned-driver model.

There is currently no automated test suite or CI configuration in this repository. The README was checked against the source; installation, workflow execution and PDF rendering were not rerun for this documentation update. Historical local setup and development notes remain in [TASK_NOTES.md](TASK_NOTES.md).

Workflow actions validate transitions, but the context flag used by `write()` is not an authorization boundary. Hardening that path is needed before relying on it against arbitrary RPC writes. Chatter provides ordinary change history, not an immutable audit ledger, and a read-only reference field in the UI does not make the reference tamper-proof.
