from odoo.tests import HttpCase, tagged

from .common import LeatherInspectionCommon


@tagged('post_install', '-at_install')
class TestLeatherInspectionBrowser(HttpCase, LeatherInspectionCommon):
    """Data-entry queue and operator review, under the accounts created in setUpClass."""

    def test_data_entry_and_operator_tours(self):
        inspection = self._assigned(self.entry_a, lot_name='LOT-TOUR')
        self.start_tour(
            '/odoo/leather-inspections',
            'leather_inspection_data_entry',
            login=self.entry_a.login,
        )
        inspection.invalidate_recordset()
        self.assertEqual(inspection.state, 'submitted')
        self.assertEqual(inspection.measured_area, 4.5)
        self.assertEqual(inspection.usable_area, 4.25)
        self.assertEqual(inspection.grade, 'a')

        self.start_tour(
            f'/odoo/leather-inspections/{inspection.id}',
            'leather_inspection_operator_review',
            login=self.operator.login,
        )
        inspection.invalidate_recordset()
        self.assertEqual(inspection.state, 'approved')
        self.assertEqual(inspection.reviewer_id, self.operator)
