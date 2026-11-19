from odoo.fields import Command


DEMO_PASSWORD = 'leather-demo'


def post_init_hook(env):
    """Load one receipt, one quality check, one inspection, the demo bag BoM, and role users.

    The receipt is a normal stock operation used as master data. Creating it is
    not an inspection action.
    """
    Inspection = env['leather.inspection']
    company = env.company
    users = {
        'leather_inspection.user_entry_a': ('Leather Data Entry A', 'leather.entry.a', 'leather_inspection.group_leather_inspection_data_entry'),
        'leather_inspection.user_entry_b': ('Leather Data Entry B', 'leather.entry.b', 'leather_inspection.group_leather_inspection_data_entry'),
        'leather_inspection.user_operator': ('Leather Module Operator', 'leather.operator', 'leather_inspection.group_leather_inspection_operator'),
        'leather_inspection.user_admin': ('Leather Administrator', 'leather.admin', 'leather_inspection.group_leather_inspection_admin'),
    }
    for xmlid, (name, login, group_xmlid) in users.items():
        _ensure_user(env, xmlid, name, login, group_xmlid, company)

    _ensure_demo_bom(env)
    if env.ref('leather_inspection.inspection_representative', raise_if_not_found=False):
        return

    hide = env.ref('leather_inspection.product_hide_calfskin').product_variant_id
    lot = env['stock.lot'].create({
        'name': 'LOT-DEMO-0001',
        'product_id': hide.id,
        'company_id': company.id,
    })
    picking = _receive(env, hide, lot, 5.0, company)
    move_line = picking.move_line_ids.filtered(lambda line: line.lot_id == lot)[:1]
    check = env['quality.check'].create(Inspection._prepare_quality_check_vals(
        hide, picking, lot, company, move_line=move_line,
    ))
    inspection = Inspection.create({
        'quality_check_id': check.id,
        'lot_id': lot.id,
        'company_id': company.id,
        'measured_area': 5.250,
        'usable_area': 4.800,
        'grade': 'a',
        'shade': 'Natural',
        'defect_notes': 'Synthetic calfskin lot for the prototype. Measurements are not stock quantities.',
    })
    entry = env.ref('leather_inspection.user_entry_a')
    inspection.action_assign_to(entry)
    env['ir.model.data']._update_xmlids([
        {'xml_id': 'leather_inspection.lot_demo_0001', 'record': lot, 'noupdate': True},
        {'xml_id': 'leather_inspection.picking_demo_receipt', 'record': picking, 'noupdate': True},
        {'xml_id': 'leather_inspection.check_demo_receipt', 'record': check, 'noupdate': True},
        {'xml_id': 'leather_inspection.inspection_representative', 'record': inspection, 'noupdate': True},
    ])


def _ensure_user(env, xmlid, name, login, group_xmlid, company):
    user = env.ref(xmlid, raise_if_not_found=False)
    if user:
        return user
    user = env['res.users'].with_context(no_reset_password=True).create({
        'name': name,
        'login': login,
        'password': DEMO_PASSWORD,
        'email': f'{login}@example.com',
        'company_id': company.id,
        'company_ids': [Command.link(company.id)],
        'group_ids': [Command.set([
            env.ref('base.group_user').id,
            env.ref(group_xmlid).id,
        ])],
    })
    env['ir.model.data']._update_xmlids([
        {'xml_id': xmlid, 'record': user, 'noupdate': True},
    ])
    return user


def _ensure_demo_bom(env):
    if env.ref('leather_inspection.bom_demo_tote', raise_if_not_found=False):
        return
    tote = env.ref('leather_inspection.product_tote')
    hide = env.ref('leather_inspection.product_hide_calfskin').product_variant_id
    lining = env.ref('leather_inspection.product_lining').product_variant_id
    hardware = env.ref('leather_inspection.product_hardware').product_variant_id
    unit = env.ref('uom.product_uom_unit')
    bom = env['mrp.bom'].create({
        'product_tmpl_id': tote.id,
        'product_id': tote.product_variant_id.id,
        'product_qty': 1.0,
        'uom_id': unit.id,
        'code': 'BOM-TOTE',
        'type': 'normal',
        'company_id': env.company.id,
        'bom_line_ids': [
            Command.create({'product_id': hide.id, 'product_qty': 1.0, 'uom_id': unit.id}),
            Command.create({'product_id': lining.id, 'product_qty': 1.0, 'uom_id': unit.id}),
            Command.create({'product_id': hardware.id, 'product_qty': 1.0, 'uom_id': unit.id}),
        ],
    })
    env['ir.model.data']._update_xmlids([
        {'xml_id': 'leather_inspection.bom_demo_tote', 'record': bom, 'noupdate': True},
    ])


def _receive(env, product, lot, qty, company):
    warehouse = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
    supplier = env.ref('stock.stock_location_suppliers')
    picking = env['stock.picking'].create({
        'picking_type_id': warehouse.in_type_id.id,
        'location_id': supplier.id,
        'location_dest_id': warehouse.lot_stock_id.id,
        'origin': 'Leather prototype receipt',
    })
    move = env['stock.move'].create({
        'product_id': product.id,
        'product_uom_qty': qty,
        'uom_id': product.uom_id.id,
        'picking_id': picking.id,
        'location_id': supplier.id,
        'location_dest_id': warehouse.lot_stock_id.id,
        'company_id': company.id,
    })
    picking.action_confirm()
    if not move.move_line_ids:
        env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': product.id,
            'quantity': qty,
            'lot_id': lot.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_id': picking.id,
            'company_id': company.id,
        })
    else:
        move.move_line_ids.write({'lot_id': lot.id, 'quantity': qty})
    move.picked = True
    picking.button_validate()
    return picking
