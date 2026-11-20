# leather_inspection

Incoming leather inspection for Odoo 20. Technical name `leather_inspection`. Depends on `web`, `quality_control` (Enterprise), and `mrp`. Version `20.0.1.1.0`.

Inspection actions update only `leather.inspection`. They do not post stock, change lot quantities, consume leather, or pass the quality check.

The repository [README](../README.md) is the handover: setup script, POS recipe, Shopify blocker, and what was run. This file is the addon contract.

## Brand

The prototype company (`base.main_company`, and the current company when the install hook loads demo data) is named **KROY**. The mark is `static/src/img/kroy-mark.png`, cropped from the supplied board. It is not redrawn. The company logo is that file, so login (`/web/binary/company_logo`, only once the logo is no longer the default), PDF report headers, and an Enterprise home menu pick it up without editing Odoo. The backend navbar and the inspection form also show the same file. If the company logo is still the default, the login page keeps an empty band (`.o_kroy_logo_slot`) where the image would be.

| Color | Hex | Where it is used |
| --- | --- | --- |
| Espresso | `#281C17` | Primary. Navbar, primary buttons, text, company `primary_color`. The mark itself is this color. |
| Cognac | `#A35935` | Accent for product materials and packaging. Material group on the inspection form, primary-button hover, inspection links. |
| Ivory | `#F2E9DC` | Light background. Login, form labels, inspection form, and the inspection list (the catalog). |
| Olive | `#596253` | Secondary accent for series and inserts. Company `secondary_color`, secondary buttons, and the top rule of the inspection sheet. The inspection form has no series or insert field. |

## Workflow

Draft → Assigned → Submitted → Approved.

Return for correction goes from Submitted back to Assigned. It requires a reason and keeps the measurements, the lot, and the assignee.

| Action | Who | Result |
| --- | --- | --- |
| Create and assign | Module operator or administrator | One draft per company, quality check, and lot. Assign moves it to a data-entry user. |
| Edit and submit | The assigned data-entry user | Only result fields, and only while Assigned. Submit locks them. |
| Return | Module operator or administrator | Submitted → Assigned, with a reason. |
| Approve | Module operator or administrator | Revalidates the results, stamps reviewer and review time. |

A normal create or write that includes a forbidden field is rejected as a whole. State, assignee, reviewer, lot, company, and the links are not directly writable. The actions check the group, the record rule, the state, and the measurements, then write with `sudo()`.

## Roles

| Group | Access |
| --- | --- |
| Data Entry | Read and write inspections where `user_id` is the current user. No create, no delete. No Inventory group, so lot and receipt are labels. |
| Module Operator | Create, read, and write in-company inspections. Implies Data Entry, Inventory / User, Lots, and Quality / User. |
| Administrator | Operator rights plus delete. `base.user_admin` is a member. |

Odoo 20 stores both ACLs and record rules on `ir.access`. The CSV header is `id,name,model_id,group_id/id,operation,domain`. `model_id` is `leather.inspection`. An empty group is a company-wide restriction.

Demo logins created on install, password `leather-demo`: `leather.entry.a`, `leather.entry.b`, `leather.operator`, `leather.admin`.

## Area

Decimal precision `Leather Area`, 3 digits, half-up.

- 1.0004 m² is stored as 1.000. 1.0005 m² is stored as 1.001.
- −0.0004 m² is stored as 0.000. −0.0006 m² is rejected.
- Usable area after rounding cannot exceed measured area.
- Drafts may be incomplete. Submit and approve require measured area above 0 m², a grade, and the zero-usable confirmation when usable area is 0.

The stock unit stays Units. m² is the inspection measurement.

## Native limits

- `quality.check.lot_id` does not exist on Odoo 20. The addon reads `lot_ids`, and `move_line_id` / `lot_line_id` when `quality_control` defines them. The receipt move line is the stock link. `lot_line_id` is filled only when its comodel is `stock.lot`.
- Form inherit: `quality_control.quality_check_view_form`, xpath `//header`, button Leather Inspection. Menu parent: `quality_control.menu_quality_root`. Implied quality group: `quality.group_quality_user`. These ids were not confirmed from Enterprise source on the machine that built this addon. A renamed id fails install.
- Uniqueness constraint `leather_inspection_company_check_lot_uniq` on `(company_id, quality_check_id, lot_id)`. Repeating create returns the existing row and does not replace measurements.
- Views are `<list>` and `<chatter/>`. The only JavaScript is the test tour in `static/tests/tours/`.

## Tests

`leather_inspection/tests/`, tag `post_install` and not `at_install`. Accounts are `new_test_user`, not the superuser, except the install test's module update and the stock fixture's superuser fallbacks inside helpers that are then exercised as the operator, the two clerks, and the manufacturing user.

```bash
odoo-bin -d leather_test --without-demo --stop-after-init \
  --addons-path=<community>,<enterprise>,<this repo> \
  --test-enable --test-tags /leather_inspection
```

Update:

```bash
odoo-bin -d leather_test --without-demo --stop-after-init \
  --addons-path=<community>,<enterprise>,<this repo> \
  -u leather_inspection
```

These commands were not run here. Enterprise `quality_control` is not installed. See the repository README for the exact blocker.
