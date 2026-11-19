from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLeatherInspectionInstall(TransactionCase):

    def test_installed_identifiers_and_representative_inspection(self):
        module = self.env['ir.module.module'].search([('name', '=', 'leather_inspection')])
        self.assertEqual(module.state, 'installed')
        for xmlid in (
            'leather_inspection.group_leather_inspection_data_entry',
            'leather_inspection.group_leather_inspection_operator',
            'leather_inspection.group_leather_inspection_admin',
            'leather_inspection.action_leather_inspection',
            'leather_inspection.menu_leather_inspection_root',
            'leather_inspection.menu_leather_inspection_quality',
            'leather_inspection.sequence_leather_inspection',
            'leather_inspection.decimal_leather_area',
            'leather_inspection.product_hide_calfskin',
            'leather_inspection.product_tote',
            'leather_inspection.bom_demo_tote',
            'leather_inspection.user_entry_a',
            'leather_inspection.user_entry_b',
            'leather_inspection.user_operator',
            'leather_inspection.user_admin',
            'leather_inspection.lot_demo_0001',
            'leather_inspection.picking_demo_receipt',
            'leather_inspection.check_demo_receipt',
            'leather_inspection.inspection_representative',
        ):
            self.assertTrue(self.env.ref(xmlid), xmlid)
        precision = self.env.ref('leather_inspection.decimal_leather_area')
        self.assertEqual(precision.name, 'Leather Area')
        self.assertEqual(precision.digits, 3)
        inspection = self.env.ref('leather_inspection.inspection_representative')
        self.assertEqual(inspection.state, 'assigned')
        self.assertEqual(inspection.lot_id.name, 'LOT-DEMO-0001')
        self.assertEqual(inspection.user_id.login, 'leather.entry.a')
        self.assertEqual(inspection.measured_area, 5.25)
        self.assertEqual(inspection.usable_area, 4.8)
        self.assertEqual(len(self.env.ref('leather_inspection.bom_demo_tote').bom_line_ids), 3)

    def test_module_update_keeps_the_record_and_effective_rights(self):
        inspection = self.env.ref('leather_inspection.inspection_representative')
        inspection.sudo().write({'shade': 'Kept across update'})
        entry = self.env.ref('leather_inspection.user_entry_a')
        operator = self.env.ref('leather_inspection.user_operator')
        self.assertTrue(entry.has_group('leather_inspection.group_leather_inspection_data_entry'))
        self.assertFalse(entry.has_group('stock.group_stock_user'))
        self.assertTrue(operator.has_group('stock.group_stock_user'))
        self.assertTrue(operator.has_group('quality.group_quality_user'))
        extra = new_test_user(
            self.env, 'entry_update',
            groups='leather_inspection.group_leather_inspection_data_entry',
        )
        module = self.env['ir.module.module'].search([('name', '=', 'leather_inspection')])
        module.button_immediate_upgrade()

        inspection = self.env.ref('leather_inspection.inspection_representative')
        self.assertEqual(inspection.shade, 'Kept across update')
        self.assertEqual(inspection.state, 'assigned')
        self.assertEqual(inspection.lot_id.name, 'LOT-DEMO-0001')
        self.assertEqual(self.env.ref('leather_inspection.decimal_leather_area').digits, 3)
        entry = self.env.ref('leather_inspection.user_entry_a')
        extra = self.env['res.users'].search([('login', '=', 'entry_update')])
        self.assertTrue(entry.has_group('leather_inspection.group_leather_inspection_data_entry'))
        self.assertFalse(entry.has_group('stock.group_stock_user'))
        self.assertTrue(extra.has_group('leather_inspection.group_leather_inspection_data_entry'))
        self.assertFalse(extra.has_group('leather_inspection.group_leather_inspection_operator'))
