from markupsafe import Markup
from odoo import _, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Confirm the quotation and notify salespersons of other quotations that
        may now have insufficient stock as a result of this confirmation."""
        # Collect products across all orders being confirmed in this call.
        product_ids = self.mapped('order_line.product_id').ids
        confirmed_order_ids = self.ids

        # Identify quotation lines for the same products in other draft/sent orders.
        affected_lines = self.env['sale.order.line']
        if product_ids:
            affected_lines = self.env['sale.order.line'].search([
                ('product_id', 'in', product_ids),
                ('order_id.state', 'in', ['draft', 'sent']),
                ('order_id', 'not in', confirmed_order_ids),
            ])

        result = super().action_confirm()

        if not affected_lines:
            return result

        # Clear the ORM cache so forecasted quantities reflect the new stock moves.
        affected_lines.invalidate_recordset(['virtual_available_at_date'])

        confirmed_names = ', '.join(self.mapped('name'))
        notified_orders = self.env['sale.order']

        for line in affected_lines:
            order = line.order_id
            if order in notified_orders:
                continue
            if (line.virtual_available_at_date or 0.0) < line.product_uom_qty:
                self._notify_stock_shortage(order, confirmed_names)
                notified_orders |= order

        return result

    def _notify_stock_shortage(self, affected_order, confirmed_names):
        """Post an internal note and schedule an activity on *affected_order*
        to alert its salesperson about a potential stock shortage."""
        # Build the HTML body keeping HTML structure in Markup and translatable
        # text in _() so the translation system never needs to handle HTML tags.
        body = Markup("""⚠️ %(title)s
            %(intro)s %(orders)s. %(review)s""") % {
            'title': _('Stock shortage warning'),
            'intro': _(
                'The following sale order(s) have just been confirmed and may have caused '
                'insufficient forecasted stock for one or more products in this quotation:'
            ),
            'orders': confirmed_names,
            'review': _('Please review product availability before proceeding.'),
        }
        affected_order.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        if affected_order.user_id:
            affected_order.activity_schedule(
                'mail.mail_activity_data_warning',
                note=_(
                    'Stock shortage detected after order(s) %(orders)s were confirmed. '
                    'Review product availability in this quotation.',
                    orders=confirmed_names,
                ),
                user_id=affected_order.user_id.id,
            )
