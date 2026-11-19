from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from .common import LeatherInspectionCommon


@tagged('post_install', '-at_install')
class TestLeatherInspectionValidation(LeatherInspectionCommon):

    def test_valid_measurements_and_equal_areas(self):
        inspection = self._assigned(lot_name='LOT-VALID')
        form = Form(inspection.with_user(self.entry_a))
        form.measured_area = 3.5
        form.usable_area = 3.5
        form.grade = 'a'
        form.shade = 'Honey'
        form.defect_notes = 'No cuts.'
        form.save()
        self.assertEqual(inspection.measured_area, 3.5)
        self.assertEqual(inspection.usable_area, 3.5)
        inspection.with_user(self.entry_a).action_submit()
        self.assertEqual(inspection.state, 'submitted')

    def test_explicit_zero_usable_area(self):
        inspection = self._assigned(lot_name='LOT-ZERO-OK')
        inspection.with_user(self.entry_a).write({
            'measured_area': 2.0,
            'usable_area': 0.0,
            'grade': 'reject',
            'zero_usable_confirmed': True,
        })
        inspection.with_user(self.entry_a).action_submit()
        self.assertEqual(inspection.state, 'submitted')
        self.assertEqual(inspection.usable_area, 0.0)

    def test_unconfirmed_zero_is_rejected(self):
        inspection = self._assigned(lot_name='LOT-ZERO-NO')
        inspection.with_user(self.entry_a).write({
            'measured_area': 2.0,
            'usable_area': 0.0,
            'grade': 'c',
        })
        with self.assertRaises(UserError, msg='Usable area is 0.000 m²'):
            inspection.with_user(self.entry_a).action_submit()
        self.assertEqual(inspection.state, 'assigned')

    def test_missing_grade_and_zero_measured_area(self):
        inspection = self._assigned(lot_name='LOT-INCOMPLETE')
        inspection.with_user(self.entry_a).write({'measured_area': 1.5, 'usable_area': 1.0})
        with self.assertRaisesRegex(UserError, 'Grade is required'):
            inspection.with_user(self.entry_a).action_submit()
        inspection.with_user(self.entry_a).write({'grade': 'b', 'measured_area': 0.0, 'usable_area': 0.0})
        with self.assertRaisesRegex(UserError, 'Measured area must be greater than 0'):
            inspection.with_user(self.entry_a).action_submit()
        self.assertEqual(inspection.state, 'assigned')

    def test_negative_values_rejected_on_form_and_orm(self):
        inspection = self._assigned(lot_name='LOT-NEG')
        with self.assertRaisesRegex(UserError, 'Measured area cannot be negative'):
            inspection.with_user(self.entry_a).write({'measured_area': -1.0})
        self.assertEqual(inspection.measured_area, 0.0)
        with self.assertRaisesRegex(UserError, 'Usable area cannot be negative'):
            inspection.with_user(self.entry_a).write({'usable_area': -0.25})
        form = Form(inspection.with_user(self.entry_a))
        with self.assertRaises(UserError):
            form.measured_area = -0.5
            form.save()
        self.assertEqual(inspection.measured_area, 0.0)

    def test_usable_area_cannot_exceed_measured(self):
        inspection = self._assigned(lot_name='LOT-OVER')
        with self.assertRaisesRegex(UserError, 'cannot exceed measured area'):
            inspection.with_user(self.entry_a).write({
                'measured_area': 1.2,
                'usable_area': 1.5,
            })
        self.assertEqual(inspection.measured_area, 0.0)
        self.assertEqual(inspection.usable_area, 0.0)

    def test_precision_boundary(self):
        """Leather Area is 3 digits, half-up. 1.0004 m² stores as 1.000; 1.0005 m² stores as 1.001."""
        inspection = self._assigned(lot_name='LOT-PREC')
        inspection.with_user(self.entry_a).write({
            'measured_area': 1.0004,
            'usable_area': 1.0004,
        })
        self.assertEqual(inspection.measured_area, 1.0)
        self.assertEqual(inspection.usable_area, 1.0)
        # -0.0004 m² rounds to 0.000 and is not a negative stored value.
        inspection.with_user(self.entry_a).write({'measured_area': -0.0004, 'usable_area': 0.0})
        self.assertEqual(inspection.measured_area, 0.0)
        with self.assertRaisesRegex(UserError, 'cannot exceed measured area'):
            inspection.with_user(self.entry_a).write({
                'measured_area': 1.0,
                'usable_area': 1.0005,
            })
        self.assertEqual(inspection.measured_area, 0.0)
        self.assertEqual(inspection.usable_area, 0.0)
        with self.assertRaisesRegex(UserError, 'cannot be negative'):
            inspection.with_user(self.entry_a).write({'measured_area': -0.0006})

    def test_draft_may_omit_grade(self):
        inspection = self._draft(lot_name='LOT-DRAFT')
        self.assertEqual(inspection.state, 'draft')
        self.assertFalse(inspection.grade)
        self.assertEqual(inspection.measured_area, 0.0)
