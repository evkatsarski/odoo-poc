from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    leather_inspection_ids = fields.One2many(
        'leather.inspection',
        'quality_check_id',
        string='Leather Inspections',
    )
    leather_inspection_count = fields.Integer(
        compute='_compute_leather_inspection_count',
        string='Leather Inspections',
    )

    @api.depends('leather_inspection_ids')
    def _compute_leather_inspection_count(self):
        for check in self:
            check.leather_inspection_count = len(check.leather_inspection_ids)

    def action_open_leather_inspection(self):
        """Open the inspection workspace for this check.

        Does not create a record, post stock, or change ``quality_state``.
        A new form is only a draft the operator still has to save.
        """
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group(
            'leather_inspection.group_leather_inspection_operator'
        ):
            raise AccessError(_(
                'Only a leather inspection operator or administrator can open the inspection from this check.'
            ))
        action = self.env['ir.actions.act_window']._for_xml_id(
            'leather_inspection.action_leather_inspection'
        )
        inspections = self.leather_inspection_ids
        if len(inspections) == 1:
            action.update({
                'res_id': inspections.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })
            return action
        if inspections:
            action['domain'] = [('id', 'in', inspections.ids)]
            return action
        context = dict(self.env.context)
        context['default_quality_check_id'] = self.id
        lots = self.env['leather.inspection']._linked_lots(self)
        if len(lots) == 1:
            context['default_lot_id'] = lots.id
        action['context'] = context
        action.update({'view_mode': 'form', 'views': [(False, 'form')]})
        return action
