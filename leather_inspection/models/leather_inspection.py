from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

# Areas are stored with decimal precision "Leather Area" (3 digits, 0.001 m²).
AREA_PRECISION_NAME = 'Leather Area'
AREA_UNIT = 'm²'

RESULT_FIELDS = frozenset({
    'measured_area',
    'usable_area',
    'grade',
    'shade',
    'defect_notes',
    'zero_usable_confirmed',
})
# Identity is chosen when the inspection is created. Workflow fields are
# written only by the validated actions, which use a private superuser write
# after the group, state, and business checks. A normal write that includes
# anything outside the allowed set is rejected as a whole.
CREATE_ALLOWED_FIELDS = RESULT_FIELDS | frozenset({
    'quality_check_id',
    'lot_id',
    'company_id',
})


class LeatherInspection(models.Model):
    _name = 'leather.inspection'
    _description = 'Leather Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='/',
        index='trigram',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('assigned', 'Assigned'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
        ],
        string='Status',
        default='draft',
        required=True,
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    quality_check_id = fields.Many2one(
        'quality.check',
        string='Quality Check',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
        readonly=True,
        groups='leather_inspection.group_leather_inspection_operator',
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
        readonly=True,
        groups='leather_inspection.group_leather_inspection_operator',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        readonly=True,
        index=True,
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Receipt',
        required=True,
        readonly=True,
        index=True,
        groups='leather_inspection.group_leather_inspection_operator',
    )
    move_line_id = fields.Many2one(
        'stock.move.line',
        string='Receipt Move Line',
        readonly=True,
        groups='leather_inspection.group_leather_inspection_operator',
    )
    # Plain labels so a data-entry user can see the lot and receipt without
    # inventory or quality-check read access. See the addon README.
    lot_label = fields.Char(string='Lot', readonly=True)
    picking_label = fields.Char(string='Receipt', readonly=True)
    quality_check_label = fields.Char(string='Quality Check', readonly=True)
    user_id = fields.Many2one(
        'res.users',
        string='Assigned User',
        readonly=True,
        index=True,
        tracking=True,
    )
    measured_area = fields.Float(
        string='Measured Area',
        digits=AREA_PRECISION_NAME,
        help='Total measured hide area in m². This is not a stock quantity.',
    )
    usable_area = fields.Float(
        string='Usable Area',
        digits=AREA_PRECISION_NAME,
        help='Usable hide area in m². This is not a stock quantity.',
    )
    grade = fields.Selection(
        [
            ('a', 'Grade A'),
            ('b', 'Grade B'),
            ('c', 'Grade C'),
            ('reject', 'Reject'),
        ],
        string='Grade',
    )
    shade = fields.Char(string='Shade')
    defect_notes = fields.Text(string='Defect Notes')
    zero_usable_confirmed = fields.Boolean(
        string='Zero usable area confirmed',
        help='Required on submission when usable area is 0 m², so a default zero is not stored as a measurement.',
    )
    return_reason = fields.Text(string='Return Reason', readonly=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer', readonly=True, copy=False)
    review_date = fields.Datetime(string='Review Time', readonly=True, copy=False)

    _company_check_lot_uniq = models.Constraint(
        'unique (company_id, quality_check_id, lot_id)',
        'An inspection already exists for this company, quality check, and leather lot.',
    )

    # -------------------------------------------------------------------------
    # Precision and link checks
    # -------------------------------------------------------------------------

    @api.model
    def _area_digits(self):
        return self.env['decimal.precision'].precision_get(AREA_PRECISION_NAME)

    @api.model
    def _format_area(self, value):
        digits = self._area_digits()
        rounded = float_round(value or 0.0, precision_digits=digits)
        return f'{rounded:.{digits}f} {AREA_UNIT}'

    @api.model
    def _round_result_vals(self, vals):
        vals = dict(vals)
        digits = self._area_digits()
        for name in ('measured_area', 'usable_area'):
            if name in vals and vals[name] not in (None, False):
                vals[name] = float_round(vals[name], precision_digits=digits)
        return vals

    @api.model
    def _check_area_bounds(self, measured, usable):
        """Reject negatives and usable area above measured area at the configured precision."""
        digits = self._area_digits()
        if float_compare(measured or 0.0, 0.0, precision_digits=digits) < 0:
            raise UserError(_(
                'Measured area cannot be negative. Current value: %(value)s.',
                value=self._format_area(measured),
            ))
        if float_compare(usable or 0.0, 0.0, precision_digits=digits) < 0:
            raise UserError(_(
                'Usable area cannot be negative. Current value: %(value)s.',
                value=self._format_area(usable),
            ))
        if float_compare(usable or 0.0, measured or 0.0, precision_digits=digits) > 0:
            raise UserError(_(
                'Usable area (%(usable)s) cannot exceed measured area (%(measured)s).',
                usable=self._format_area(usable),
                measured=self._format_area(measured),
            ))

    def _check_ready_for_review(self):
        digits = self._area_digits()
        for inspection in self:
            measured = inspection.measured_area
            usable = inspection.usable_area
            inspection._check_area_bounds(measured, usable)
            if float_compare(measured, 0.0, precision_digits=digits) <= 0:
                raise UserError(_(
                    'Measured area must be greater than 0 %(unit)s before submission. Current value: %(value)s.',
                    unit=AREA_UNIT,
                    value=inspection._format_area(measured),
                ))
            if not inspection.grade:
                raise UserError(_('Grade is required before submission.'))
            if float_is_zero(usable, precision_digits=digits) and not inspection.zero_usable_confirmed:
                raise UserError(_(
                    'Usable area is %(value)s. Confirm that zero usable area is intentional before submission.',
                    value=inspection._format_area(usable),
                ))

    @api.model
    def _linked_lots(self, check):
        """Lots named on the quality check, across the Odoo 20 field names."""
        lots = self.env['stock.lot']
        if 'lot_ids' in check._fields:
            lots |= check.lot_ids
        if 'lot_id' in check._fields and check.lot_id:
            # Removed on quality.check in Odoo 19. Kept so an older build still validates.
            lots |= check.lot_id
        if 'lot_line_id' in check._fields and check.lot_line_id:
            lots |= check.lot_line_id
        if 'move_line_id' in check._fields and check.move_line_id.lot_id:
            lots |= check.move_line_id.lot_id
        return lots

    @api.model
    def _validate_links(self, check, lot, company):
        """Return ``(product, picking, move_line)`` or raise a field-specific error.

        Odoo 20 ``quality.check`` has no ``lot_id``. Lots are ``lot_ids`` on the
        quality module, with ``move_line_id`` and ``lot_line_id`` added by
        quality_control. The authoritative stock link is a move line of the
        incoming receipt. An empty ``lot_ids`` is accepted when that move line
        exists, because receipt checks do not always copy the lot onto the check.
        """
        if not check or not check.exists():
            raise UserError(_('A quality check is required.'))
        if not lot or not lot.exists():
            raise UserError(_('A leather lot is required.'))
        if not company:
            raise UserError(_('A company is required.'))
        if check.company_id and check.company_id != company:
            raise UserError(_(
                'Quality check %(check)s belongs to %(check_company)s, not %(company)s.',
                check=check.display_name,
                check_company=check.company_id.display_name,
                company=company.display_name,
            ))
        if lot.company_id and lot.company_id != company:
            raise UserError(_(
                'Leather lot %(lot)s belongs to %(lot_company)s, not %(company)s.',
                lot=lot.display_name,
                lot_company=lot.company_id.display_name,
                company=company.display_name,
            ))
        picking = check.picking_id
        if not picking:
            raise UserError(_(
                'Quality check %(check)s must be linked to an incoming receipt.',
                check=check.display_name,
            ))
        if picking.company_id and picking.company_id != company:
            raise UserError(_(
                'Receipt %(picking)s belongs to %(picking_company)s, not %(company)s.',
                picking=picking.display_name,
                picking_company=picking.company_id.display_name,
                company=company.display_name,
            ))
        if picking.picking_type_code != 'incoming':
            raise UserError(_(
                'Receipt %(picking)s is not an incoming receipt.',
                picking=picking.display_name,
            ))
        if check.product_id and lot.product_id != check.product_id:
            raise UserError(_(
                'Leather lot %(lot)s is for product %(lot_product)s, not quality check product %(check_product)s.',
                lot=lot.display_name,
                lot_product=lot.product_id.display_name,
                check_product=check.product_id.display_name,
            ))
        product = check.product_id or lot.product_id
        if not product:
            raise UserError(_('The quality check and the leather lot have no product.'))
        if lot.product_id != product:
            raise UserError(_(
                'Leather lot %(lot)s is for product %(lot_product)s, not %(product)s.',
                lot=lot.display_name,
                lot_product=lot.product_id.display_name,
                product=product.display_name,
            ))

        move_line = self.env['stock.move.line']
        if 'move_line_id' in check._fields and check.move_line_id:
            move_line = check.move_line_id
            if move_line.picking_id and move_line.picking_id != picking:
                raise UserError(_(
                    'The move line on quality check %(check)s is not on receipt %(picking)s.',
                    check=check.display_name,
                    picking=picking.display_name,
                ))
            if move_line.lot_id and move_line.lot_id != lot:
                raise UserError(_(
                    'The move line on quality check %(check)s is for lot %(line_lot)s, not %(lot)s.',
                    check=check.display_name,
                    line_lot=move_line.lot_id.display_name,
                    lot=lot.display_name,
                ))
            if move_line.product_id and move_line.product_id != product:
                raise UserError(_(
                    'The move line on quality check %(check)s is for product %(line_product)s, not %(product)s.',
                    check=check.display_name,
                    line_product=move_line.product_id.display_name,
                    product=product.display_name,
                ))

        receipt_lines = picking.move_line_ids.filtered(
            lambda line: line.lot_id == lot and line.product_id == product
        )
        if not receipt_lines and not (move_line and move_line.lot_id == lot):
            raise UserError(_(
                'Lot %(lot)s is not on a move line of incoming receipt %(picking)s.',
                lot=lot.display_name,
                picking=picking.display_name,
            ))
        named_lots = self._linked_lots(check)
        # move_line_id.lot_id is already part of _linked_lots. When the only
        # named lot is that same move line, the receipt link above is enough.
        # A non-empty lot_ids / lot_line_id that omits this lot is inconsistent.
        explicit_lots = self.env['stock.lot']
        if 'lot_ids' in check._fields:
            explicit_lots |= check.lot_ids
        if 'lot_id' in check._fields and check.lot_id:
            explicit_lots |= check.lot_id
        if 'lot_line_id' in check._fields and check.lot_line_id:
            explicit_lots |= check.lot_line_id
        if explicit_lots and lot not in explicit_lots:
            raise UserError(_(
                'Lot %(lot)s is not one of the lots on quality check %(check)s.',
                lot=lot.display_name,
                check=check.display_name,
            ))
        if not named_lots and not receipt_lines:
            raise UserError(_(
                'Lot %(lot)s is not linked to quality check %(check)s or receipt %(picking)s.',
                lot=lot.display_name,
                check=check.display_name,
                picking=picking.display_name,
            ))
        return product, picking, (receipt_lines[:1] or move_line)

    @api.model
    def _prepare_quality_check_vals(self, product, picking, lot, company, move_line=None):
        """Vals for a manual incoming check. Adapts to the fields on this build."""
        check_model = self.env['quality.check']
        vals = {
            'product_id': product.id,
            'picking_id': picking.id,
            'company_id': company.id,
        }
        if 'lot_ids' in check_model._fields:
            vals['lot_ids'] = [fields.Command.set([lot.id])]
        elif 'lot_id' in check_model._fields:
            vals['lot_id'] = lot.id
        lot_line = check_model._fields.get('lot_line_id')
        if lot_line and lot_line.type == 'many2one' and lot_line.comodel_name == 'stock.lot':
            vals['lot_line_id'] = lot.id
        move_line_field = check_model._fields.get('move_line_id')
        if (
            move_line
            and move_line_field
            and move_line_field.type == 'many2one'
            and move_line_field.comodel_name == 'stock.move.line'
        ):
            vals['move_line_id'] = move_line.id
        if 'title' in check_model._fields:
            vals['title'] = _('Incoming leather inspection')
        for name, field in check_model._fields.items():
            if name in vals or not field.required or field.default:
                continue
            if name in ('id', 'name', 'display_name'):
                continue
            if field.type == 'many2one':
                found = self.env[field.comodel_name].search([], limit=1)
                if found:
                    vals[name] = found.id
            elif field.type == 'selection':
                selection = field.selection(check_model) if callable(field.selection) else field.selection
                if selection:
                    vals[name] = selection[0][0]
        test_type_model = self.env.get('quality.point.test_type')
        if test_type_model is not None and 'test_type_id' in check_model._fields:
            domain = []
            if 'technical_name' in test_type_model._fields:
                domain = [('technical_name', '=', 'passfail')]
            test_type = test_type_model.search(domain, limit=1) or test_type_model.search([], limit=1)
            if test_type:
                vals['test_type_id'] = test_type.id
        return vals

    # -------------------------------------------------------------------------
    # ORM guards
    # -------------------------------------------------------------------------

    def _allowed_write_fields(self):
        self.ensure_one()
        if (
            self.state == 'assigned'
            and self.user_id == self.env.user
            and self.env.user.has_group('leather_inspection.group_leather_inspection_data_entry')
        ):
            return RESULT_FIELDS
        return frozenset()

    def _reject_forbidden(self, vals, allowed, verb):
        forbidden = set(vals) - allowed
        if not forbidden:
            return
        names = ', '.join(sorted(forbidden))
        raise UserError(_(
            'This %(verb)s was rejected because it includes fields that cannot be changed directly: %(fields)s. No fields were updated.',
            verb=verb,
            fields=names,
        ))

    @api.model_create_multi
    def create(self, vals_list):
        existing_ids = []
        for vals in vals_list:
            vals = dict(vals)
            self._reject_forbidden(vals, CREATE_ALLOWED_FIELDS, _('create'))
            company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
            check = self.env['quality.check'].browse(vals.get('quality_check_id'))
            lot = self.env['stock.lot'].browse(vals.get('lot_id'))
            product, picking, move_line = self._validate_links(check, lot, company)
            existing = self.search([
                ('company_id', '=', company.id),
                ('quality_check_id', '=', check.id),
                ('lot_id', '=', lot.id),
            ], limit=1)
            if existing:
                existing_ids.append(existing.id)
                continue
            vals.update({
                'company_id': company.id,
                'quality_check_id': check.id,
                'lot_id': lot.id,
                'product_id': product.id,
                'picking_id': picking.id,
                'move_line_id': move_line.id or False,
                'lot_label': lot.name,
                'picking_label': picking.name,
                'quality_check_label': check.name or check.display_name,
                'name': self.env['ir.sequence'].next_by_code('leather.inspection') or _('New'),
                'state': 'draft',
            })
            vals = self._round_result_vals(vals)
            self._check_area_bounds(vals.get('measured_area') or 0.0, vals.get('usable_area') or 0.0)
            created = super().create([vals])
            existing_ids.append(created.id)
        return self.browse(existing_ids)

    def write(self, vals):
        if not vals:
            return True
        vals = dict(vals)
        if not self.env.su:
            for inspection in self:
                inspection._reject_forbidden(vals, inspection._allowed_write_fields(), _('write'))
        vals = self._round_result_vals(vals)
        if {'measured_area', 'usable_area'} & set(vals):
            for inspection in self:
                measured = vals['measured_area'] if 'measured_area' in vals else inspection.measured_area
                usable = vals['usable_area'] if 'usable_area' in vals else inspection.usable_area
                inspection._check_area_bounds(measured, usable)
        return super().write(vals)

    def unlink(self):
        # Deletion is an ACL concern (administrator only). No stock side effects.
        return super().unlink()

    # -------------------------------------------------------------------------
    # Workflow actions
    # -------------------------------------------------------------------------

    def _ensure_operator(self):
        if self.env.su:
            return
        if not self.env.user.has_group('leather_inspection.group_leather_inspection_operator'):
            raise AccessError(_(
                'Only a leather inspection operator or administrator can perform this action.'
            ))

    def _ensure_state(self, states, action_label):
        labels = dict(self._fields['state'].selection)
        expected = ', '.join(labels[state] for state in states)
        for inspection in self:
            if inspection.state not in states:
                raise UserError(_(
                    'Inspection %(name)s is %(state)s. %(action)s is only available from %(expected)s.',
                    name=inspection.name,
                    state=labels.get(inspection.state, inspection.state),
                    action=action_label,
                    expected=expected,
                ))

    def action_open_assign_wizard(self):
        self.ensure_one()
        self._ensure_operator()
        self._ensure_state({'draft'}, _('Assign'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign'),
            'res_model': 'leather.inspection.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_inspection_id': self.id},
        }

    def action_assign_to(self, user):
        """Move Draft to Assigned. ``user`` must be a data-entry user in the company."""
        if not user:
            raise UserError(_('Choose a data-entry user to assign.'))
        if isinstance(user, int):
            user = self.env['res.users'].browse(user)
        self._ensure_operator()
        self._ensure_state({'draft'}, _('Assign'))
        if not user.has_group('leather_inspection.group_leather_inspection_data_entry'):
            raise UserError(_(
                'Assign the inspection to a user in Leather Inspection / Data Entry.'
            ))
        for inspection in self:
            if inspection.company_id not in user.company_ids:
                raise UserError(_(
                    'User %(user)s is not in company %(company)s.',
                    user=user.display_name,
                    company=inspection.company_id.display_name,
                ))
        self.sudo().write({'user_id': user.id, 'state': 'assigned'})
        return True

    def action_submit(self):
        if not self.env.su:
            if not self.env.user.has_group('leather_inspection.group_leather_inspection_data_entry'):
                raise AccessError(_('Only the assigned data-entry user can submit this inspection.'))
            for inspection in self:
                if inspection.user_id != self.env.user:
                    raise AccessError(_('Only the assigned data-entry user can submit this inspection.'))
        self._ensure_state({'assigned'}, _('Submit for Review'))
        self._check_ready_for_review()
        self.sudo().write({'state': 'submitted'})
        return True

    def action_open_return_wizard(self):
        self.ensure_one()
        self._ensure_operator()
        self._ensure_state({'submitted'}, _('Return for Correction'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return for Correction'),
            'res_model': 'leather.inspection.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_inspection_id': self.id},
        }

    def action_return_for_correction(self, reason):
        self._ensure_operator()
        self._ensure_state({'submitted'}, _('Return for Correction'))
        reason = (reason or '').strip()
        if not reason:
            raise UserError(_('A correction reason is required to return this inspection.'))
        # Measurements, lot, and assignee stay as they are. Stock is not touched.
        self.sudo().write({'state': 'assigned', 'return_reason': reason})
        return True

    def action_approve(self):
        self._ensure_operator()
        self._ensure_state({'submitted'}, _('Approve'))
        self._check_ready_for_review()
        self.sudo().write({
            'state': 'approved',
            'reviewer_id': self.env.user.id,
            'review_date': fields.Datetime.now(),
        })
        return True
