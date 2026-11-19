from odoo import api, fields, models


class LeatherInspectionAssignWizard(models.TransientModel):
    _name = 'leather.inspection.assign.wizard'
    _description = 'Assign Leather Inspection'

    inspection_id = fields.Many2one(
        'leather.inspection',
        string='Inspection',
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(related='inspection_id.company_id')
    allowed_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_allowed_user_ids',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Data-entry user',
        required=True,
        domain="[('id', 'in', allowed_user_ids)]",
    )

    @api.depends('inspection_id', 'inspection_id.company_id')
    def _compute_allowed_user_ids(self):
        group = self.env.ref('leather_inspection.group_leather_inspection_data_entry')
        candidates = group.all_user_ids.filtered(lambda user: not user.share)
        for wizard in self:
            company = wizard.inspection_id.company_id
            wizard.allowed_user_ids = candidates.filtered(
                lambda user, company=company: company and company in user.company_ids
            )

    def action_assign(self):
        self.ensure_one()
        self.inspection_id.action_assign_to(self.user_id)
        return {'type': 'ir.actions.act_window_close'}
