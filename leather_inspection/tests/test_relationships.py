from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import LeatherInspectionCommon


@tagged('post_install', '-at_install')
class TestLeatherInspectionRelationships(LeatherInspectionCommon):

    def test_lot_on_receipt_is_accepted(self):
        inspection = self._draft(lot_name='LOT-LINKED')
        self.assertEqual(inspection.product_id, self.hide)
        self.assertEqual(inspection.picking_id.picking_type_code, 'incoming')
        self.assertEqual(inspection.move_line_id.lot_id, inspection.lot_id)
        self.assertEqual(inspection.lot_label, 'LOT-LINKED')

    def test_empty_check_lots_still_accept_the_receipt_line(self):
        inspection = self._draft(lot_name='LOT-NOLIST', include_lots=False)
        self.assertEqual(inspection.move_line_id.lot_id.name, 'LOT-NOLIST')

    def test_wrong_product_is_rejected(self):
        other = self._product('Other hide', tracking='lot')
        lot = self._lot(other, 'LOT-OTHER-PRODUCT')
        receipt_lot = self._lot(self.hide, 'LOT-RIGHT-PRODUCT')
        picking = self._receive(self.hide, receipt_lot, 1.0)
        # Put the wrong lot on a check that names the calfskin product.
        check = self._check(self.hide, picking, receipt_lot)
        with self.assertRaisesRegex(UserError, 'not quality check product'):
            self.env['leather.inspection'].with_user(self.operator).create(
                self._inspection_vals(check, lot)
            )

    def test_wrong_receipt_is_rejected(self):
        lot = self._lot(self.hide, 'LOT-RECEIPT')
        incoming = self._receive(self.hide, lot, 1.0)
        outgoing = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        check = self._check(self.hide, incoming, lot)
        check.picking_id = outgoing
        with self.assertRaisesRegex(UserError, 'not an incoming receipt'):
            self.env['leather.inspection'].with_user(self.operator).create(
                self._inspection_vals(check, lot)
            )

    def test_lot_missing_from_receipt_is_rejected(self):
        received = self._lot(self.hide, 'LOT-ON-RECEIPT')
        absent = self._lot(self.hide, 'LOT-NOT-ON-RECEIPT')
        picking = self._receive(self.hide, received, 1.0)
        check = self._check(self.hide, picking, received, include_lots=False)
        with self.assertRaisesRegex(UserError, 'not on a move line'):
            self.env['leather.inspection'].with_user(self.operator).create(
                self._inspection_vals(check, absent)
            )

    def test_wrong_company_is_rejected(self):
        inspection = self._draft(lot_name='LOT-COMPANY')
        other = self.env['res.company'].create({'name': 'Other Tannery'})
        with self.assertRaisesRegex(UserError, 'belongs to'):
            self.env['leather.inspection'].with_user(self.operator).create({
                'quality_check_id': inspection.quality_check_id.id,
                'lot_id': inspection.lot_id.id,
                'company_id': other.id,
            })

    def test_repeated_create_returns_the_same_inspection(self):
        inspection = self._draft(lot_name='LOT-ONCE', user=self.operator)
        again = self.env['leather.inspection'].with_user(self.operator).create(
            self._inspection_vals(
                inspection.quality_check_id,
                inspection.lot_id,
                measured_area=9.0,
            )
        )
        self.assertEqual(again, inspection)
        self.assertEqual(inspection.measured_area, 0.0)
        self.assertEqual(self.env['leather.inspection'].search_count([
            ('quality_check_id', '=', inspection.quality_check_id.id),
            ('lot_id', '=', inspection.lot_id.id),
        ]), 1)

    def test_database_uniqueness_constraint(self):
        inspection = self._draft(lot_name='LOT-SQL')
        self.env.cr.execute(
            """
            SELECT conname
              FROM pg_constraint
             WHERE conrelid = 'leather_inspection'::regclass
               AND contype = 'u'
            """
        )
        self.assertIn(
            'leather_inspection_company_check_lot_uniq',
            [row[0] for row in self.env.cr.fetchall()],
        )
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env.cr.execute(
                    """
                    INSERT INTO leather_inspection (
                        name, state, company_id, quality_check_id, lot_id,
                        product_id, picking_id, measured_area, usable_area,
                        zero_usable_confirmed, create_uid, write_uid,
                        create_date, write_date
                    ) VALUES (
                        %s, 'draft', %s, %s, %s, %s, %s, 1, 1, FALSE,
                        %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC'
                    )
                    """,
                    (
                        'LI/DUP',
                        inspection.company_id.id,
                        inspection.quality_check_id.id,
                        inspection.lot_id.id,
                        inspection.product_id.id,
                        inspection.picking_id.id,
                        self.env.uid,
                        self.env.uid,
                    ),
                )
        self.assertEqual(self.env['leather.inspection'].search_count([
            ('lot_id', '=', inspection.lot_id.id),
        ]), 1)
