from odoo.tests import new_test_user, TransactionCase


class LeatherInspectionCommon(TransactionCase):
    """Synthetic hide, receipt, and non-superuser accounts shared by the suites."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.company.id),
        ], limit=1)
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.unit = cls.env.ref('uom.product_uom_unit')
        cls.category = cls.env.ref('product.product_category_goods')
        cls.hide = cls._product('Test calfskin hide', tracking='lot')
        cls.bag = cls._product('Test tote')
        cls.entry_a = new_test_user(
            cls.env, 'entry_a',
            groups='leather_inspection.group_leather_inspection_data_entry',
            lang='en_US',
        )
        cls.entry_b = new_test_user(
            cls.env, 'entry_b',
            groups='leather_inspection.group_leather_inspection_data_entry',
            lang='en_US',
        )
        cls.operator = new_test_user(
            cls.env, 'leather_op',
            groups='leather_inspection.group_leather_inspection_operator',
            lang='en_US',
        )
        cls.admin = new_test_user(
            cls.env, 'leather_adm',
            groups='leather_inspection.group_leather_inspection_admin',
            lang='en_US',
        )
        cls.maker = new_test_user(
            cls.env, 'leather_maker',
            groups='mrp.group_mrp_user,stock.group_production_lot',
            lang='en_US',
        )
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.bag.product_tmpl_id.id,
            'product_id': cls.bag.id,
            'product_qty': 1.0,
            'uom_id': cls.unit.id,
            'code': 'BOM-TEST-TOTE',
            'type': 'normal',
            'company_id': cls.company.id,
            'bom_line_ids': [(0, 0, {
                'product_id': cls.hide.id,
                'product_qty': 1.0,
                'uom_id': cls.unit.id,
            })],
        })

    @classmethod
    def _product(cls, name, tracking=False):
        vals = {
            'name': name,
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.unit.id,
            'categ_id': cls.category.id,
        }
        if tracking:
            vals['tracking'] = tracking
        return cls.env['product.template'].create(vals).product_variant_id

    def _receive(self, product, lot, qty, user=None):
        env = self.env if user is None else self.env(user=user.id)
        picking = env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'origin': lot.name,
        })
        move = env['stock.move'].create({
            'product_id': product.id,
            'product_uom_qty': qty,
            'uom_id': product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'company_id': self.company.id,
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
                'company_id': self.company.id,
            })
        else:
            move.move_line_ids.write({'lot_id': lot.id, 'quantity': qty})
        move.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        return picking

    def _lot(self, product, name):
        return self.env['stock.lot'].create({
            'name': name,
            'product_id': product.id,
            'company_id': self.company.id,
        })

    def _check(self, product, picking, lot, user=None, include_lots=True):
        env = self.env if user is None else self.env(user=user.id)
        vals = env['leather.inspection']._prepare_quality_check_vals(
            product,
            picking,
            lot,
            self.company,
            move_line=picking.move_line_ids.filtered(lambda line: line.lot_id == lot)[:1],
        )
        if not include_lots:
            vals.pop('lot_ids', None)
            vals.pop('lot_id', None)
            vals.pop('lot_line_id', None)
        return env['quality.check'].create(vals)

    def _inspection_vals(self, check, lot, **extra):
        vals = {
            'quality_check_id': check.id,
            'lot_id': lot.id,
            'company_id': self.company.id,
        }
        vals.update(extra)
        return vals

    def _draft(self, lot_name='LOT-TEST', qty=5.0, user=None, include_lots=True):
        user = user or self.operator
        lot = self._lot(self.hide, lot_name)
        picking = self._receive(self.hide, lot, qty, user=user)
        check = self._check(self.hide, picking, lot, user=user, include_lots=include_lots)
        inspection = self.env['leather.inspection'].with_user(user).create(
            self._inspection_vals(check, lot)
        )
        return inspection

    def _assigned(self, entry=None, **kwargs):
        entry = entry or self.entry_a
        inspection = self._draft(**kwargs)
        inspection.with_user(self.operator).action_assign_to(entry)
        return inspection
