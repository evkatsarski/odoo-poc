# Leather inspection prototype

Odoo 20 addon `leather_inspection` for incoming leather lots at a luxury leather-goods workshop. Inspection records measurements only. Stock, the quality pass or fail, and manufacturing consumption stay native Odoo operations.

This repository holds the custom addon. It does not contain Odoo Community, Odoo Enterprise, the Shopify connector, credentials, or database dumps.

## What is running here

Community Odoo 20.0 is installed outside the repo at `/opt/odoo`, revision `fa2c1d6e67fff519d450f43271717ab1c93dac9b` (19 Nov 2026, 11:10 Europe/Sofia). PostgreSQL 16 is local. Database `leather_proto` was initialized without demo data. Inventory, Manufacturing, and Point of Sale are installed.

`leather_inspection` is not installed. It depends on Enterprise `quality_control`, and no Enterprise addons are on this machine. See [What ran, and what is pending](#what-ran-and-what-is-pending).

## Workflow

| State | Who acts | What happens |
| --- | --- | --- |
| Draft | Module operator or administrator | Created from one incoming quality check and one leather lot. Product and receipt are copied from those records. |
| Assigned | Module operator or administrator | Assign wizard picks a data-entry user in the same company. |
| Submitted | That assigned user | Result fields are validated, then the record locks. |
| Assigned again | Module operator or administrator | Return for correction requires a reason. Measurements, lot, and assignee stay. |
| Approved | Module operator or administrator | Results are validated again. Reviewer and review time are stamped. |

Buttons on the form follow the same rules. The ORM rejects a write that contains any field outside the allowed set, and it does not apply the other fields in that write.

Submitting, returning, and approving do not post a receipt, change a lot quantity, consume leather, or set `quality.check.quality_state`. Passing the check is the standard Quality action. Consuming the hide is a manufacturing order.

## Role matrix

| Group | Sees | Can do | Does not |
| --- | --- | --- | --- |
| Leather Inspection / Data Entry | Inspections assigned to them. Lot, receipt, and quality check as plain labels. | Edit result fields while Assigned, then Submit for Review. | Create, delete, assign, approve, return, or open inventory and quality records. Not an Inventory user. |
| Leather Inspection / Module Operator | In-company inspections, including drafts and submissions. Lot, receipt, quality check, and receipt move line as real links. | Create, assign, return, approve. Inventory / User and Quality / User come from the implied groups. | Delete inspections. |
| Leather Inspection / Administrator | Same as the module operator. | Delete inspections. Implied operator rights. `base.user_admin` is a member. | User administration stays on Settings. |

Two demo data-entry users, `leather.entry.a` and `leather.entry.b`, prove the queue is per user. Operators and administrators also imply Data Entry, so they appear in the assignee list. The clerks to assign are the two data-entry users.

Record rules are `ir.access` rows (Odoo 20 has no `ir.rule`). A row with an empty group is a global company restriction. Group rows are combined. Technical model name in the CSV is `leather.inspection`.

## Area precision

Decimal precision **Leather Area** is 3 digits (0.001 m²). Values are rounded half-up before they are stored, using Odoo's `float_round`.

| Entered | Stored |
| --- | --- |
| 1.0004 m² | 1.000 m² |
| 1.0005 m² | 1.001 m² |
| −0.0004 m² | 0.000 m², accepted |
| −0.0006 m² | −0.001 m², rejected |

Usable area cannot exceed measured area after rounding, so measured 1.000 and usable 1.0005 is rejected. A draft may omit the grade and may have a zero measured area. Submission and approval require measured area greater than 0 m², a grade, and the zero-usable confirmation when usable area rounds to 0.

Stock is still in Units. m² is not the product unit of measure.

## Native model limits

Checked against this Community tree and the Odoo 20 Quality documentation. Enterprise source is not on the machine, so the Quality names below are the ones the addon adapts to at runtime (`'field' in check._fields`).

- `quality.check` has no `lot_id` (removed in Odoo 19). Lots are `lot_ids`. `quality_control` adds `move_line_id` and `lot_line_id`. The inspection accepts an empty `lot_ids` when the incoming receipt move line carries the lot. A non-empty lot list that omits the lot is rejected.
- The quality-check form inherit is `quality_control.quality_check_view_form`, xpath `//header`. The operator menu parent is `quality_control.menu_quality_root`. The operator group implies `quality.group_quality_user`. Those xml ids are the long-standing Enterprise ids and were not re-read from Enterprise source here. If a 20.0 build renamed them, install stops on the missing xml id.
- Data-entry users are not given Inventory. They cannot read `stock.lot` or `stock.picking`, so the form shows `lot_label`, `picking_label`, and `quality_check_label` instead of the links. Operators see the links.
- Views use `<list>` and `<chatter/>`. Uniqueness is `models.Constraint` named `leather_inspection_company_check_lot_uniq` on `(company_id, quality_check_id, lot_id)`. A repeated create returns that row and does not overwrite measurements.
- One company (`base.main_company` on a fresh database, named KROY by this addon) and one warehouse (`stock.warehouse0`).

## Demo data loaded by the addon

Fifteen synthetic products. Hides `HIDE-CALF` and `HIDE-LAMB` are lot-tracked. Components: `LINING`, `HARDWARE`, `THREAD`, `EDGE`, `ZIPPER`, `DUST`, `BOX`. Finished goods, saleable: `TOTE`, `CARD`, `BELT`, `WALLET`, `STRAP`, `POUCH`.

Bill of materials `BOM-TOTE`: one demo tote = one calfskin hide + one lining + one hardware kit, in Units.

Representative inspection `LI/…` on lot `LOT-DEMO-0001` (5 units received), measured 5.250 m², usable 4.800 m², grade A, shade Natural, assigned to `leather.entry.a`.

Demo users, password `leather-demo`:

| Login | Group |
| --- | --- |
| `leather.entry.a` | Data Entry |
| `leather.entry.b` | Data Entry |
| `leather.operator` | Module Operator |
| `leather.admin` | Administrator |

Database manager and the `admin` user on this disposable database use the stock Odoo password `admin`.

## Install and update

`quality_control` and `mrp` must be on the addons path. Enterprise stays on the licensee path and is not copied into this repo.

```bash
export ENTERPRISE_ADDONS=/opt/odoo-enterprise   # must contain quality_control
./setup/bootstrap.sh
```

The script initializes database `leather_proto` (override with `DB_NAME`) and installs `leather_inspection` and `point_of_sale`. `--without-demo` is a boolean.

Update, then the tests, on a disposable database:

```bash
/opt/odoo-venv/bin/python /opt/odoo/odoo-bin -d leather_test --without-demo --stop-after-init \
  --addons-path=/opt/odoo/addons,/opt/odoo/odoo/addons,$ENTERPRISE_ADDONS,/path/to/odoo-poc \
  -u leather_inspection

/opt/odoo-venv/bin/python /opt/odoo/odoo-bin -d leather_test --without-demo --stop-after-init \
  --addons-path=/opt/odoo/addons,/opt/odoo/odoo/addons,$ENTERPRISE_ADDONS,/path/to/odoo-poc \
  --test-enable --test-tags /leather_inspection
```

Module update from the UI or from `ir.module.module.button_immediate_upgrade` is the same entry point the install test calls.

Server, after a successful install:

```bash
/opt/odoo-venv/bin/python /opt/odoo/odoo-bin -d leather_proto --http-port=8069 \
  --addons-path=/opt/odoo/addons,/opt/odoo/odoo/addons,$ENTERPRISE_ADDONS,/path/to/odoo-poc \
  --data-dir=/opt/odoo-data
```

List: `/odoo/leather-inspections`. Form: `/odoo/leather-inspections/<id>`. Operators also have Quality → Leather Inspections.

## POS sale and return

`point_of_sale` is Community and is not a dependency of this addon. On `leather_proto` it is installed. As user `admin`, one register **Workshop register** was created on the company warehouse, a storable **Demo tote bag** (`TOTE-POS`, list price 120) was stocked at 5 units, and a session was opened. A cash sale of one tote posted (on-hand 5 → 4, order total 138 including tax, state done). The refund of that order posted (on-hand 4 → 5, state done). The session then closed. This was the POS ORM (`pos.config.open_ui`, `pos.order`, `pos.make.payment`, `pos.order.refund`, `pos.session.close_session_from_ui`), not a click-through of the register screen. The addon catalog product `TOTE` is separate and is not loaded until `leather_inspection` installs. Hide quantity still changes only when a manufacturing order consumes it.

## Shopify

Pending. There are no Shopify credentials, no Odoo.sh staging project, and the official connector is not vendored here. Do not treat a mock as acceptance. The automated tests do not call Shopify.

## What ran, and what is pending

Ran locally:

- PostgreSQL 16 and a Community 20.0 checkout at the revision above.
- `leather_proto` initialized with `stock` and `mrp`, `--without-demo`, exit 0. Log `/tmp/odoo-init.log`. `point_of_sale` was installed afterwards, exit 0. On 19 Nov 2026 at 16:04 Europe/Sofia the server on port 8069 returned HTTP 200 for `/web/login`, and `admin` / `admin` authenticated (uid 2, database `leather_proto`).
- POS sale and refund of `TOTE-POS` as described above. On-hand returned to 5. Session state `closed`.
- `python3 -m compileall -q leather_inspection` exited 0.
- Install of `leather_inspection` on `leather_proto` (addons path includes this repo, no Enterprise path):

```
WARNING leather_proto odoo.modules.module_graph: module leather_inspection: some depends are not loaded (quality_control), skipped
ERROR leather_proto odoo.modules.loading: Some modules have inconsistent states, some dependencies may be missing: ['leather_inspection']
```

The process exit code was 0. `ir_module_module.state` for `quality_control` is `uninstallable`. `leather_inspection` was left `to install` and was set back to `uninstalled` so later server starts do not keep retrying it. Log `/tmp/odoo-install-leather.log`.

Not run, because Enterprise `quality_control` is absent:

- Every test under `leather_inspection/tests/` (`post_install`, not `at_install`): install/update, validation, relationships, roles, transitions, stock and traceability, and the two web tours.
- The Quality check form inherit, the Quality menu, and `quality.group_quality_user`.
- A screenshot of the inspection form. None was taken.
- The POS touchscreen. The sale and refund above used the ORM.
- Odoo.sh staging and the Shopify connector (no credentials, connector not in this repo).

## Layout

```
leather_inspection/          the addon
setup/bootstrap.sh           install once Enterprise addons are available
```

Addon detail, including the same workflow, lives in `leather_inspection/README.md`.
