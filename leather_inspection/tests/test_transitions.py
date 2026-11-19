from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import LeatherInspectionCommon


@tagged('post_install', '-at_install')
class TestLeatherInspectionTransitions(LeatherInspectionCommon):

    def _fill(self, inspection, user):
        inspection.with_user(user).write({
            'measured_area': 4.5,
            'usable_area': 4.25,
            'grade': 'a',
            'shade': 'Cognac',
            'defect_notes': 'Small mark on the edge.',
        })

    def test_assign_submit_return_resubmit_approve(self):
        inspection = self._draft(lot_name='LOT-FLOW')
        self.assertEqual(inspection.state, 'draft')
        wizard = self.env['leather.inspection.assign.wizard'].with_user(self.operator).create({
            'inspection_id': inspection.id,
            'user_id': self.entry_a.id,
        })
        self.assertIn(self.entry_a, wizard.allowed_user_ids)
        wizard.action_assign()
        self.assertEqual(inspection.state, 'assigned')
        self.assertEqual(inspection.user_id, self.entry_a)

        self._fill(inspection, self.entry_a)
        inspection.with_user(self.entry_a).action_submit()
        self.assertEqual(inspection.state, 'submitted')

        with self.assertRaises(UserError):
            inspection.with_user(self.entry_a).write({'shade': 'Changed after submit'})
        self.assertEqual(inspection.shade, 'Cognac')

        return_wizard = self.env['leather.inspection.return.wizard'].with_user(self.operator).create({
            'inspection_id': inspection.id,
            'reason': 'Recheck the edge mark.',
        })
        return_wizard.action_return()
        self.assertEqual(inspection.state, 'assigned')
        self.assertEqual(inspection.return_reason, 'Recheck the edge mark.')
        self.assertEqual(inspection.measured_area, 4.5)
        self.assertEqual(inspection.usable_area, 4.25)
        self.assertEqual(inspection.user_id, self.entry_a)

        inspection.with_user(self.entry_a).write({'shade': 'Cognac, rechecked'})
        inspection.with_user(self.entry_a).action_submit()
        inspection.with_user(self.admin).action_approve()
        self.assertEqual(inspection.state, 'approved')
        self.assertEqual(inspection.reviewer_id, self.admin)
        self.assertTrue(inspection.review_date)
        with self.assertRaises(UserError):
            inspection.with_user(self.entry_a).write({'grade': 'b'})
        self.assertEqual(inspection.grade, 'a')

    def test_illegal_and_repeated_transitions(self):
        inspection = self._draft(lot_name='LOT-ILLEGAL')
        with self.assertRaisesRegex(UserError, 'only available from'):
            inspection.with_user(self.entry_a).action_submit()
        with self.assertRaisesRegex(UserError, 'only available from'):
            inspection.with_user(self.operator).action_approve()
        with self.assertRaises(UserError):
            inspection.with_user(self.operator).action_return_for_correction('Too early')
        self.assertEqual(inspection.state, 'draft')
        self.assertFalse(inspection.return_reason)

        inspection.with_user(self.operator).action_assign_to(self.entry_a)
        with self.assertRaisesRegex(UserError, 'only available from'):
            inspection.with_user(self.operator).action_assign_to(self.entry_b)
        self.assertEqual(inspection.user_id, self.entry_a)

        self._fill(inspection, self.entry_a)
        inspection.with_user(self.entry_a).action_submit()
        with self.assertRaisesRegex(UserError, 'only available from'):
            inspection.with_user(self.entry_a).action_submit()
        inspection.with_user(self.operator).action_approve()
        with self.assertRaisesRegex(UserError, 'only available from'):
            inspection.with_user(self.operator).action_approve()
        with self.assertRaises(UserError):
            inspection.with_user(self.operator).action_return_for_correction('After approval')
        self.assertEqual(inspection.state, 'approved')
        self.assertEqual(inspection.reviewer_id, self.operator)

    def test_return_requires_a_reason_and_direct_state_is_rejected(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-REASON')
        self._fill(inspection, self.entry_a)
        inspection.with_user(self.entry_a).action_submit()
        with self.assertRaisesRegex(UserError, 'correction reason'):
            inspection.with_user(self.operator).action_return_for_correction('   ')
        self.assertEqual(inspection.state, 'submitted')
        with self.assertRaises(UserError):
            inspection.with_user(self.operator).write({'state': 'approved'})
        with self.assertRaises(UserError):
            inspection.with_user(self.entry_a).write({'state': 'approved', 'grade': 'reject'})
        self.assertEqual(inspection.state, 'submitted')
        self.assertEqual(inspection.grade, 'a')

    def test_approve_rechecks_the_results(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-RECHECK')
        inspection.with_user(self.entry_a).write({
            'measured_area': 1.0,
            'usable_area': 0.0,
            'grade': 'c',
        })
        inspection.sudo().write({'state': 'submitted'})
        with self.assertRaisesRegex(UserError, 'Confirm that zero usable area'):
            inspection.with_user(self.operator).action_approve()
        self.assertEqual(inspection.state, 'submitted')
        self.assertFalse(inspection.reviewer_id)

    def test_data_entry_cannot_assign_or_open_the_wizard(self):
        inspection = self._draft(lot_name='LOT-NOASSIGN')
        with self.assertRaises(AccessError):
            inspection.with_user(self.entry_a).action_assign_to(self.entry_b)
        with self.assertRaises(AccessError):
            self.env['leather.inspection.assign.wizard'].with_user(self.entry_a).create({
                'inspection_id': inspection.id,
                'user_id': self.entry_b.id,
            })
        self.assertEqual(inspection.state, 'draft')
        self.assertFalse(inspection.user_id)

    def test_quality_check_entry_point_does_not_create_or_pass(self):
        inspection = self._draft(lot_name='LOT-OPEN')
        check = inspection.quality_check_id
        state_before = check.quality_state if 'quality_state' in check._fields else None
        action = check.with_user(self.operator).action_open_leather_inspection()
        self.assertEqual(action['res_id'], inspection.id)
        self.assertEqual(check.quality_state if 'quality_state' in check._fields else None, state_before)

        lot = self._lot(self.hide, 'LOT-OPEN-NEW')
        picking = self._receive(self.hide, lot, 1.0, user=self.operator)
        fresh = self._check(self.hide, picking, lot, user=self.operator)
        before = self.env['leather.inspection'].search_count([])
        opened = fresh.with_user(self.operator).action_open_leather_inspection()
        self.assertFalse(opened.get('res_id'))
        self.assertEqual(opened['context']['default_quality_check_id'], fresh.id)
        self.assertEqual(opened['context']['default_lot_id'], lot.id)
        self.assertEqual(self.env['leather.inspection'].search_count([]), before)
        if 'quality_state' in fresh._fields:
            self.assertNotEqual(fresh.quality_state, 'pass')
        with self.assertRaises(AccessError):
            fresh.with_user(self.entry_a).action_open_leather_inspection()
