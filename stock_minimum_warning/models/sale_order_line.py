from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_in_draft_quotations = fields.Float(
        string='Qty in Draft Quotations',
        compute='_compute_qty_in_draft_quotations',
        digits='Product Unit of Measure',
        help='Total quantity of this product reserved in other unconfirmed quotations (draft/sent).',
    )
    draft_quotation_warning = fields.Boolean(
        string='Draft Quotation Warning',
        compute='_compute_draft_quotation_warning',
        help=(
            'True when there is enough total forecasted stock to cover this line but, '
            'after subtracting quantities already in other unconfirmed quotations, '
            'the net forecasted stock falls below the quantity to deliver.'
        ),
    )
    # Translated UI labels computed server-side so the browser always receives
    # them in the logged-in user's language, regardless of the JS translation bundle.
    draft_quotation_label_unconfirmed = fields.Char(
        compute='_compute_draft_quotation_labels',
    )
    draft_quotation_label_net_forecasted = fields.Char(
        compute='_compute_draft_quotation_labels',
    )
    draft_quotation_label_view_drafts = fields.Char(
        compute='_compute_draft_quotation_labels',
    )

    @api.depends('product_id', 'order_id')
    def _compute_qty_in_draft_quotations(self):
        """Compute the total quantity of each product in other draft/sent quotations.

        Processes the recordset in batches grouped by order to minimise the number
        of database queries (one query per unique order in the batch).
        """
        lines_by_order = {}
        for line in self:
            key = line.order_id.id or 0
            lines_by_order.setdefault(key, self.env['sale.order.line'])
            lines_by_order[key] |= line

        for order_id, lines in lines_by_order.items():
            product_ids = lines.filtered('product_id').mapped('product_id.id')
            if not product_ids:
                for line in lines:
                    line.qty_in_draft_quotations = 0.0
                continue

            domain = [
                ('product_id', 'in', product_ids),
                ('order_id.state', 'in', ['draft', 'sent']),
            ]
            if order_id:
                domain.append(('order_id', '!=', order_id))

            draft_lines = self.env['sale.order.line'].search(domain)

            qty_by_product = {}
            for dl in draft_lines:
                pid = dl.product_id.id
                try:
                    qty = dl.product_uom._compute_quantity(
                        dl.product_uom_qty,
                        dl.product_id.uom_id,
                    )
                except Exception:
                    qty = dl.product_uom_qty
                qty_by_product[pid] = qty_by_product.get(pid, 0.0) + qty

            for line in lines:
                if not line.product_id:
                    line.qty_in_draft_quotations = 0.0
                else:
                    line.qty_in_draft_quotations = qty_by_product.get(
                        line.product_id.id, 0.0
                    )

    @api.depends(
        'qty_in_draft_quotations',
        'virtual_available_at_date',
        'qty_to_deliver',
        'order_id.state',
        'is_mto',
    )
    def _compute_draft_quotation_warning(self):
        """Yellow warning: enough total stock for this line alone, but the net
        forecasted quantity (forecasted − demand in other draft quotations) is
        less than what this line needs to deliver."""
        for line in self:
            if line.order_id.state not in ('draft', 'sent') or line.is_mto:
                line.draft_quotation_warning = False
                continue
            virtual_qty = line.virtual_available_at_date or 0.0
            draft_qty = line.qty_in_draft_quotations or 0.0
            qty_to_deliver = line.qty_to_deliver or 0.0
            net_forecasted = virtual_qty - draft_qty
            line.draft_quotation_warning = bool(
                virtual_qty >= qty_to_deliver      # not already red
                and net_forecasted < qty_to_deliver  # but net is insufficient
            )

    @api.depends()
    def _compute_draft_quotation_labels(self):
        """Return UI labels translated in the current user's language.

        Computing labels server-side guarantees the correct language regardless
        of whether the JS translation bundle has been reloaded.
        """
        label_unconfirmed = _("In Unconfirmed Quotations")
        label_net_forecasted = _("Net Forecasted")
        label_view_drafts = _("View Draft Quotations")
        for line in self:
            line.draft_quotation_label_unconfirmed = label_unconfirmed
            line.draft_quotation_label_net_forecasted = label_net_forecasted
            line.draft_quotation_label_view_drafts = label_view_drafts

    def action_view_draft_quotations(self):
        """Return a window action listing unconfirmed quotations that contain this product."""
        self.ensure_one()
        draft_order_ids = self.env['sale.order.line'].search([
            ('product_id', '=', self.product_id.id),
            ('order_id.state', 'in', ['draft', 'sent']),
            ('order_id', '!=', self.order_id.id),
        ]).mapped('order_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Draft Quotations for %s') % self.product_id.display_name,
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', draft_order_ids)],
            'context': {
                'create': False,
                'delete': False,
            },
            'target': 'current',
        }
