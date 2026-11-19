from odoo import fields, models


class LeatherInspectionReturnWizard(models.TransientModel):
    _name = 'leather.inspection.return.wizard'
    _description = 'Return Leather Inspection for Correction'

    inspection_id = fields.Many2one(
        'leather.inspection',
        string='Inspection',
        required=True,
        readonly=True,
    )
    reason = fields.Text(string='Correction reason', required=True)

    def action_return(self):
        self.ensure_one()
        self.inspection_id.action_return_for_correction(self.reason)
        return {'type': 'ir.actions.act_window_close'}
