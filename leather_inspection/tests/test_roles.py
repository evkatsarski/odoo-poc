from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import LeatherInspectionCommon


@tagged('post_install', '-at_install')
class TestLeatherInspectionRoles(LeatherInspectionCommon):

    def test_inherited_groups(self):
        self.assertTrue(self.entry_a.has_group('base.group_user'))
        self.assertFalse(self.entry_a.has_group('stock.group_stock_user'))
        self.assertFalse(self.entry_a.has_group('leather_inspection.group_leather_inspection_operator'))
        self.assertTrue(self.operator.has_group('leather_inspection.group_leather_inspection_data_entry'))
        self.assertTrue(self.operator.has_group('stock.group_stock_user'))
        self.assertTrue(self.operator.has_group('quality.group_quality_user'))
        operator_group = self.env.ref('leather_inspection.group_leather_inspection_operator')
        self.assertNotIn(operator_group, self.admin.group_ids)
        self.assertTrue(self.admin.has_group('leather_inspection.group_leather_inspection_operator'))
        self.assertTrue(self.admin.has_group('leather_inspection.group_leather_inspection_data_entry'))

    def test_entry_a_can_work_the_assigned_queue_only(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-QUEUE-A')
        found = self.env['leather.inspection'].with_user(self.entry_a).search([
            ('id', '=', inspection.id),
        ])
        self.assertEqual(found, inspection)
        inspection.with_user(self.entry_a).write({
            'measured_area': 2.0,
            'usable_area': 1.5,
            'grade': 'a',
        })
        inspection.with_user(self.entry_a).action_submit()
        self.assertEqual(inspection.state, 'submitted')
        self.assertEqual(inspection.with_user(self.entry_a).lot_label, inspection.lot_id.name)
        with self.assertRaises(AccessError):
            inspection.with_user(self.entry_a).lot_id.id

    def test_entry_b_cannot_discover_or_touch_a(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-QUEUE-B')
        hidden = self.env['leather.inspection'].with_user(self.entry_b).search([
            ('id', '=', inspection.id),
        ])
        self.assertFalse(hidden)
        with self.assertRaises(AccessError):
            inspection.with_user(self.entry_b).read(['name'])
        with self.assertRaises(AccessError):
            inspection.with_user(self.entry_b).write({'shade': 'Stolen'})
        self.assertFalse(inspection.shade)

    def test_create_and_delete_denied_for_data_entry(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-ACL')
        with self.assertRaises(AccessError):
            self.env['leather.inspection'].with_user(self.entry_a).create(
                self._inspection_vals(inspection.quality_check_id, inspection.lot_id)
            )
        with self.assertRaises(AccessError):
            inspection.with_user(self.entry_a).unlink()
        with self.assertRaises(AccessError):
            inspection.with_user(self.operator).unlink()
        self.assertTrue(inspection.exists())

    def test_direct_protected_writes_change_nothing(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-GUARD')
        inspection.with_user(self.entry_a).write({'measured_area': 2.0, 'usable_area': 1.0, 'grade': 'b'})
        original = {
            'measured_area': inspection.measured_area,
            'state': inspection.state,
            'user_id': inspection.user_id.id,
            'lot_id': inspection.lot_id.id,
            'reviewer_id': inspection.reviewer_id.id,
        }
        with self.assertRaisesRegex(UserError, 'No fields were updated'):
            inspection.with_user(self.entry_a).write({
                'measured_area': 8.0,
                'state': 'approved',
                'user_id': self.entry_b.id,
                'reviewer_id': self.entry_a.id,
            })
        inspection.invalidate_recordset()
        self.assertEqual(inspection.measured_area, original['measured_area'])
        self.assertEqual(inspection.state, original['state'])
        self.assertEqual(inspection.user_id.id, original['user_id'])
        self.assertEqual(inspection.lot_id.id, original['lot_id'])
        self.assertFalse(inspection.reviewer_id)
        with self.assertRaises(UserError):
            inspection.with_user(self.operator).write({'measured_area': 3.0, 'shade': 'Operator edit'})
        self.assertEqual(inspection.measured_area, original['measured_area'])
        self.assertFalse(inspection.shade)

    def test_data_entry_cannot_run_a_privileged_action(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-PRIV')
        inspection.with_user(self.entry_a).write({
            'measured_area': 2.0,
            'usable_area': 2.0,
            'grade': 'a',
        })
        inspection.with_user(self.entry_a).action_submit()
        with self.assertRaises(AccessError):
            inspection.with_user(self.entry_a).action_approve()
        with self.assertRaises(AccessError):
            inspection.with_user(self.entry_b).action_approve()
        self.assertEqual(inspection.state, 'submitted')
        self.assertFalse(inspection.reviewer_id)

    def test_operator_and_admin_can_review(self):
        first = self._assigned(self.entry_a, lot_name='LOT-OP')
        first.with_user(self.entry_a).write({
            'measured_area': 1.0, 'usable_area': 1.0, 'grade': 'a',
        })
        first.with_user(self.entry_a).action_submit()
        first.with_user(self.operator).action_approve()
        self.assertEqual(first.state, 'approved')
        self.assertEqual(first.reviewer_id, self.operator)

        second = self._assigned(self.entry_b, lot_name='LOT-ADM')
        second.with_user(self.entry_b).write({
            'measured_area': 1.0, 'usable_area': 1.0, 'grade': 'b',
        })
        second.with_user(self.entry_b).action_submit()
        second.with_user(self.admin).action_approve()
        self.assertEqual(second.reviewer_id, self.admin)
        spare = self._draft(lot_name='LOT-DEL')
        spare.with_user(self.admin).unlink()
        self.assertFalse(spare.exists())

    def test_create_rejects_workflow_fields_without_inserting(self):
        inspection = self._draft(lot_name='LOT-CREATE-GUARD')
        other = self._lot(self.hide, 'LOT-CREATE-GUARD-2')
        self._receive(self.hide, other, 1.0)
        check = self._check(self.hide, inspection.picking_id, inspection.lot_id)
        before = self.env['leather.inspection'].search_count([])
        with self.assertRaisesRegex(UserError, 'No fields were updated'):
            self.env['leather.inspection'].with_user(self.operator).create({
                'quality_check_id': check.id,
                'lot_id': other.id,
                'state': 'approved',
            })
        self.assertEqual(self.env['leather.inspection'].search_count([]), before)
