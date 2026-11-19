from odoo.tests import tagged

from .common import LeatherInspectionCommon


@tagged('post_install', '-at_install')
class TestLeatherInspectionStock(LeatherInspectionCommon):

    def _available(self, product, lot):
        return self.env['stock.quant']._get_available_quantity(
            product, self.warehouse.lot_stock_id, lot_id=lot,
        )

    def _finish_production(self, production):
        action = production.button_mark_done()
        for _step in range(3):
            if production.state == 'done' or not isinstance(action, dict) or not action.get('res_model'):
                break
            wizard = self.env[action['res_model']].with_user(self.maker).with_context(
                action.get('context') or {}
            ).create({})
            if hasattr(wizard, 'action_confirm'):
                action = wizard.action_confirm()
            elif hasattr(wizard, 'action_close_mo'):
                action = wizard.action_close_mo()
            else:
                break
        return production

    def test_inspection_does_not_post_stock_and_manufacturing_consumes_the_lot(self):
        lot = self._lot(self.hide, 'LOT-CONSUME')
        picking = self._receive(self.hide, lot, 2.0, user=self.maker)
        check = self._check(self.hide, picking, lot, user=self.operator)
        inspection = self.env['leather.inspection'].with_user(self.operator).create(
            self._inspection_vals(check, lot)
        )
        self.assertEqual(self._available(self.hide, lot), 2.0)
        moves_before = self.env['stock.move'].search_count([('product_id', '=', self.hide.id)])
        quality_before = check.quality_state if 'quality_state' in check._fields else None

        inspection.with_user(self.operator).action_assign_to(self.entry_a)
        inspection.with_user(self.entry_a).write({
            'measured_area': 2.0,
            'usable_area': 1.8,
            'grade': 'b',
        })
        inspection.with_user(self.entry_a).action_submit()
        inspection.with_user(self.operator).action_return_for_correction('Confirm the shade.')
        inspection.with_user(self.entry_a).write({'shade': 'Tan'})
        inspection.with_user(self.entry_a).action_submit()
        inspection.with_user(self.operator).action_approve()

        self.assertEqual(inspection.state, 'approved')
        self.assertEqual(self._available(self.hide, lot), 2.0)
        self.assertEqual(
            self.env['stock.move'].search_count([('product_id', '=', self.hide.id)]),
            moves_before,
        )
        if 'quality_state' in check._fields:
            self.assertEqual(check.quality_state, quality_before)
            self.assertNotEqual(check.quality_state, 'pass')

        production = self.env['mrp.production'].with_user(self.maker).create({
            'product_id': self.bag.id,
            'bom_id': self.bom.id,
            'product_qty': 1.0,
        })
        production.action_confirm()
        production.action_assign()
        raw = production.move_raw_ids.filtered(lambda move: move.product_id == self.hide)
        self.assertEqual(len(raw), 1)
        if not raw.move_line_ids:
            self.env['stock.move.line'].with_user(self.maker).create({
                'move_id': raw.id,
                'product_id': self.hide.id,
                'quantity': 1.0,
                'lot_id': lot.id,
                'location_id': raw.location_id.id,
                'location_dest_id': raw.location_dest_id.id,
                'company_id': self.company.id,
            })
        else:
            raw.move_line_ids.with_user(self.maker).write({'lot_id': lot.id, 'quantity': 1.0})
        production.qty_producing = 1.0
        raw.picked = True
        self._finish_production(production)

        self.assertEqual(production.state, 'done')
        self.assertEqual(production.qty_produced, 1.0)
        consumed_lines = raw.move_line_ids.filtered(lambda line: line.state == 'done' and line.lot_id == lot)
        self.assertTrue(consumed_lines)
        self.assertEqual(sum(consumed_lines.mapped('quantity')), 1.0)
        self.assertEqual(self._available(self.hide, lot), 1.0)
        self.assertEqual(inspection.state, 'approved')
        self.assertEqual(inspection.measured_area, 2.0)
        if 'quality_state' in check._fields:
            self.assertEqual(check.quality_state, quality_before)

        report = self.env['stock.traceability.report'].with_user(self.maker).get_lines(
            model_name='stock.lot', record_id=lot.id,
        )
        reported = {line['record_id'] for line in report}
        receipt_line = picking.move_line_ids.filtered(lambda line: line.lot_id == lot)
        self.assertTrue(set(receipt_line.ids) & reported)
        self.assertTrue(set(consumed_lines.ids) & reported)
