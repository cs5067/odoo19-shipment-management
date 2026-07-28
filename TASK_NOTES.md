# Task Notes — Shipment Management

Odoo 19 module for a logistics team to register shipment requests, move them through a
lifecycle by clicking buttons, and print a shipment order for the driver.

---

## Context

**What I set out to build.** A self-contained Odoo 19 module covering the assignment's
ten requirements:

1. Shipment **types** (name, code, category), maintained only by the team lead, and
   archivable.
2. Shipment **requests** with an automatic unique reference number, recording customer,
   type, origin, destination, pickup date, and delivery date.
3. One shipment carries **multiple cargo items** (description, quantity, weight, volume).
4. The shipment shows **total weight and volume** that stay correct automatically as items
   are added, changed, or removed.
5. A **lifecycle** (Preparing → With Courier → On the Way → Delivered) advanced through
   buttons — the status field cannot be edited directly.
6. A shipment **cannot leave Preparing without cargo** — attempting it shows a clear error.
7. **Status changes are recorded** in the record history so anyone can see when and how it
   progressed.
8. Two roles: a **Shipment User** (create/manage requests) and a **Shipment Manager**
   (everything a user can, plus types). No data is open to every user by default.
9. A **complete, usable interface**: list, a grouped kanban board where every lifecycle
   stage is visible even when empty, a form with status bar and history, search/filters by
   status, type, and customer, all reachable from a clear menu.
10. The shipment order can be **printed as a PDF** with reference, customer, route, cargo
    items, and totals.

**Assumptions I made** (worth confirming with the team):

- **Item weight and volume are per unit.** Each line stores the weight/volume of one unit;
  the line total is `quantity × unit value`, and the shipment total sums the lines. If the
  team records weight as an already-totalled figure per line, one multiplication in
  `shipment.item` needs to change.
- **Quantity, weight, and volume are all mandatory and must be > 0.** The brief lists all
  three as properties of a cargo item, and physically anything with weight occupies space —
  a line claiming otherwise is a data-entry error, not a special case. This closed a real
  loophole found while testing: a "ghost shipment" (0 kg, 0 m³ totals) could previously
  reach the courier. Small items simply take small real values (an envelope: 0.05 kg,
  0.001 m³).
- **Delivery date cannot be before pickup date** — added as a sanity guard; remove
  `_check_dates` if the team wants to allow it.
- **The customer is Odoo's built-in contact** (`res.partner`), reused rather than
  reinvented, so shipments share the same customer list as the rest of the system.

**Two states added beyond the original spec**, both as deliberate product decisions after
using the first version:

- **Draft.** A registered request is not yet an active shipment. It starts in Draft
  (editable, saved, waiting) and a **Confirm** button moves it into Preparing — the same
  pattern as a quotation becoming a sales order. Without this, requests were born as if the
  warehouse was already packing them, which didn't match how the work actually happens.
- **Cancelled.** Real shipments get called off. Cancelling keeps the record and its history
  (deleting would erase the audit trail requirement 7 depends on); a **Reset to Draft**
  button revives a cancelled request.

---

## What I did

- Built the full module: **3 models, 2 roles, 4 views, 1 sequence, 1 PDF report**, no
  custom JavaScript.
- **Types** are managed under *Shipments → Configuration* and are visible-but-read-only to
  regular users; only managers can create or edit them.
- **Requests** get their reference automatically on save, prefixed by the shipment type's
  code so the reference is self-describing (e.g. `EXP/2026/00001` — an express shipment
  registered in 2026). The number comes from one shared yearly counter across all types,
  and the reference never changes afterwards, even if the type's code is edited. The
  reference is always issued by the system — a value sent by a client is ignored — and the
  database enforces that references are unique.
- **Items** are entered as lines inside the request; **total weight and volume recompute
  themselves** live as lines change, and show both in the list and on the form.
- The **lifecycle** is Draft → Preparing → With Courier → On The Way → Delivered, plus
  Cancelled. Each stage advances by a button, shown one at a time in the header, with a
  status bar across the top.
- **Empty shipments are blocked**: handing a shipment to the courier with no cargo raises a
  clear error, and items can't be saved with a zero or negative quantity.
- **Every status change is logged automatically** in the record's chatter — who changed it,
  from what, to what, and when — visible to anyone who opens the shipment.
- **Two security roles** wired to Odoo 19's privilege system, with an access matrix giving
  users full control of requests but read-only on types.
- A **driver's PDF** ("Shipment Order") with a scannable barcode, From/Deliver-To blocks
  (including the customer's address and phone), a numbered cargo table with totals, and
  driver / receiver / prepared-by signature blocks.
- **A grouped kanban board** alongside the list — shipments grouped by lifecycle stage,
  with every stage column visible even when it's empty. Card dragging is disabled on
  purpose: the status may only move through the buttons, so a drag can't sidestep the
  guards.
- **The status field is locked to the buttons.** Editing `state` directly — from any
  client, even as admin — is refused; every transition funnels through one guarded method,
  and a new request can only ever start as a draft.
- **Guards that hold outside the UI.** State transitions, deletion, and cargo edits are all
  enforced in the model (not just hidden in the view), so they can't be bypassed by a stale
  browser tab or a direct API call. Details in the caveats below.
- **Input validation from a "careless user" walkthrough.** After deliberately trying to
  misuse the app, these are now refused: cargo lines with zero weight or volume, a shipment whose
  origin equals its destination (case- and space-insensitive), a pickup date in the past,
  duplicate shipment-type names, and type codes that only differ by case or spacing (codes
  are trimmed and upper-cased on save; blank names/codes are rejected). Same-day delivery
  (pickup = delivery date) was deliberately left valid — it's a real service, not an error.
- **Actual delivery timestamp.** A read-only "Delivered On" field records the exact moment
  a shipment is marked delivered — the real arrival time next to the planned delivery date.
  It shows on the form once delivered (and as an optional list column), and clears if a
  cancelled shipment is reset to draft.

**Verification.** Before every deployment I installed the module onto a throwaway database
inside the container and ran the full flow in an Odoo shell — reference assignment, each
illegal transition blocked, zero-quantity blocked, totals math, the happy path to
Delivered, cargo-lock, deletion rules, cancel/reset, and PDF rendering — then upgraded the
live `logistics` database only after it all passed.

---

## Findings, caveats, and setup

### Notable findings

- **View rules are not security.** In Odoo, `readonly`/`invisible` in a view only affect
  the browser; the server does not enforce them. Anything that must be true is enforced in
  Python or in the database. Concretely:
  - Each `action_*` method checks the **current** state before advancing, so a shipment
    can't skip stages or move backwards (e.g. a second user's stale tab can't re-deliver a
    delivered shipment).
  - `shipment.item` blocks create/write/unlink once the shipment has left preparation, so
    the cargo (and therefore the stored totals) of a shipped or delivered shipment can't be
    silently rewritten.
  - Deletion is blocked for any shipment past Draft/Cancelled (`@api.ondelete`), so a
    delivered shipment and its history can't be erased.
- **A zero-quantity line defeats a naive "has items?" check** — that's why requirement 6 is
  enforced by *both* an "at least one item" check and a "quantity > 0" constraint.
- **Odoo 19 specifics that differ from older tutorials:** security groups attach to a
  `res.groups.privilege` (not `category_id`); list views use `<list>` (not `<tree>`);
  table-level rules use `models.Constraint` (not `_sql_constraints`); search-view
  `<group>` no longer takes `expand`/`string`.
- **The PDF is laid out with HTML `<table>`, not Bootstrap grid,** because Odoo's PDF
  engine (wkhtmltopdf) renders flexbox/`row`/`col` unreliably — a two-column grid collapsed
  to one column in a real render. The barcode is generated in-process and embedded as a
  data URI rather than fetched from `/report/barcode`, so it renders in every context.

### Caveats / unfinished

- **Assumption to confirm:** item weight/volume being per-unit (see Context). This is the
  one thing that would change stored numbers if the team's convention differs.
- **Deliberately not built** (out of scope per the brief, or trimmed on purpose to keep the
  module focused): pricing/rating, fleet or accounting integration, customer portal,
  multi-company, carrier APIs (all explicitly out of scope); plus calendar views, reporting
  dashboards/KPIs, customer email notifications, and a courier/driver field ("who
  physically has the shipment" lives on the printed order's signature line, not in the
  database — a conscious trade-off). Notifications would need an SMTP server and a mail
  template; the courier field is one `Many2one` plus a line on the hand-over button.
- **One-time cosmetic hiccup:** if a browser session was left parked on a view type that
  was later removed (an earlier build briefly had a calendar view), reloading can show
  "insufficient fields for calendar view." It's a stale-session artifact, not a module bug
  — enter fresh via *Shipments* in the menu and it's gone.
- **Origin and destination are free-text** (`Char`), not structured locations. Fine for the
  spec; if the team later wants pick-lists or geocoding, they'd become `Many2one` fields.

### Setup — install and try it

Prerequisites: Docker Desktop running. The dev stack (Odoo 19 + Postgres 16) is defined in
`../docker-compose.yml`, which mounts this module into the Odoo container automatically.

```bash
# 1. From the folder that contains docker-compose.yml (the parent of this module):
cd "path/to/untitled folder"
docker compose up -d                 # starts Odoo on http://localhost:8069

# 2. First time only: open http://localhost:8069, create a database named "logistics"
#    (uncheck demo data), and set your admin login/password.

# 3. Install the module:
#    In the browser: Apps → (remove the "Apps" filter) → search "Shipment" → Activate.
#    Or from the command line:
docker exec untitledfolder-odoo-1 odoo \
  --db_host db --db_user odoo --db_password odoo \
  -d logistics -i shipment_management --stop-after-init
docker compose restart odoo
```

**Give yourself the role:** *Settings → Users → your user →* set **Shipment Management** to
*Manager*, save, and refresh.

**Try the flow:**

1. *Shipments → Configuration → Shipment Types* → create one (e.g. name `Express`,
   code `EXP`, category Express).
2. *Shipments → Shipment Requests → New* → pick customer, type, origin, destination, dates.
   Save — the reference fills in as `EXP/2026/00001` (type code / year / number).
3. **Confirm** → then **Hand to Courier** *before adding items* → you'll get the no-cargo
   error (requirement 6).
4. Add a couple of items; watch the totals compute. Hand to Courier → Start Transit →
   Mark Delivered.
5. Read the **chatter** at the bottom — every status change is logged with who and when.
6. **Print → Shipment Order** for the driver's PDF.

**The development loop:** edit files → `docker compose restart odoo` for Python changes, or
*Apps → Shipment Management → Upgrade* for XML/CSV changes → hard-refresh the browser. Data
files (XML/CSV) load at install/upgrade time, not continuously. **Test schema changes on a
throwaway database first** (`-d scratch -i shipment_management`) before upgrading
`logistics`.

---

## Data model and why

Three models belong to the module. The customer is Odoo's built-in `res.partner`, and the
status history rides on Odoo's `mail.thread` — both reused on purpose rather than rebuilt.

```
res.partner ──┐
              ├──< shipment.request >──< shipment.item
shipment.type─┘
```

### `shipment.type` — the catalog (requirement 1)

Name, `code` (unique, enforced by the database), and `category` (a fixed Selection). Has an
`active` flag so retired types are archived, not deleted. It's a small reference table so it
lives on its own — that's what lets managers own it while regular users only read it.

### `shipment.request` — the document (requirements 2, 4, 5, 6, 7)

The centre of the module. Holds the customer and type (both `Many2one`), the route and
dates, the reference `name`, and the `state`.

- **Reference** is assigned in `create()`: the type's code is prepended to a yearly
  `ir.sequence` ("year/number"), giving `EXP/2026/00001`, protected by a unique constraint
  — automatic, self-describing, non-forgeable, collision-free even if two people save at
  once (the counter is shared across types, so numbers can never collide).
- **Totals** are stored computed fields that depend on the item lines, so they're always
  correct and can be shown in lists without recalculating.
- **State** is a plain Selection; the buttons call methods that validate the transition.
  There's no workflow engine — a field, buttons, and guarded methods are simpler and are
  how Odoo itself models lifecycles now.
- **History** comes free: the model inherits `mail.thread` and the important fields are
  marked `tracking=True`, so every change is written to the chatter automatically —
  requirement 7 with no custom history table.

### `shipment.item` — the cargo lines (requirements 3, 4)

Description, quantity, per-unit weight and volume, and computed line totals. Linked to its
shipment by a `Many2one` with `ondelete="cascade"` — a line has no meaning without its
parent, so deleting a (draft) shipment cleans up its lines. Constraints keep quantity,
weight, and volume all > 0, and create/write/unlink are blocked once the shipment has left
preparation so a closed shipment's numbers stay fixed.

### Why this shape

- **One request → many items** is the natural one-to-many of the domain, and it's what
  makes the automatic totals a simple sum.
- **Types are separate** so configuration (manager-owned) is cleanly divided from
  operations (everyone), which is exactly what requirements 1 and 8 ask for.
- **Reusing `res.partner` and `mail.thread`** means the module inherits Odoo's contact
  management and a battle-tested audit trail instead of duplicating them — less code, fewer
  bugs, and it plays well with the rest of an Odoo install.
- **Foreign-key behaviour encodes intent:** customer and type are `RESTRICT` (you can't
  delete something a shipment still points at, so history stays readable); items are
  `CASCADE` (they live and die with their shipment).
