from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_method = fields.Many2one('account.journal', string='Méthode de paiement')
    wp_id = fields.Char('Identifiant', readonly=True)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            invoice_id = order._create_invoice_ecom_posted()
            self.send_invoice_mail(invoice_id)
            available = self.check_availability(order)

            if order.payment_method.name in ['Carte bancaire', 'Paypal']:
                self.do_register_payment(invoice_id)

            if available:
                pickings = []
                self.validate_pick(pickings, order)

        return res

    def send_invoice_mail(self, invoice_object):

        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        lang = False

        if template:
            lang = template._render_lang(invoice_object.ids)[invoice_object.id]

        ctx = dict(
            mark_invoice_as_sent=True,
            active_ids=invoice_object.ids,
            custom_layout="mail.mail_notification_paynow",
            model_description=invoice_object.with_context(lang=lang).type_name,
            force_email=True,
            default_res_model='account.move',
            default_use_template=bool(template),
        )
        values = {
            'model': 'account.move',
            'res_id': invoice_object.id,
            'template_id': template and template.id or False,
            'composition_mode': 'comment',
        }

        wizard = self.env['account.invoice.send'].with_context(ctx).create(values)
        wizard._compute_composition_mode()
        wizard.onchange_template_id()
        wizard.onchange_is_email()
        wizard._send_email()

    def validate_pick(self, pickings, order):

        for p in order.picking_ids:
            loc = 'WH/PICK/'
            if loc in p.name:
                pickings.append(p)

        immediate_transfer_line_ids = []
        for picking in pickings:
            immediate_transfer_line_ids.append([0, False, {
                'picking_id': picking.id,
                'to_immediate': True
            }])
        res1 = self.env['stock.immediate.transfer'].create({
            'pick_ids': [(4, p.id) for p in pickings],
            'show_transfers': False,
            'immediate_transfer_line_ids': immediate_transfer_line_ids
        })

        return res1.with_context(button_validate_picking_ids=res1.pick_ids.ids).process()

    def check_availability(self, order):
        check = True
        for o_line in order.order_line:
            product = o_line.product_id
            product_type = self.env['product.template'].search([('id', '=', product.id)])
            if product_type.type in ['product', 'consu']:
                x = o_line.product_uom_qty
                rec = self.env['stock.quant'].search([('product_id', '=', product.id), ('location_id.name', '=', 'Stock')])
                y = rec.available_quantity
                check = (y >= x)
            if not check:
                break
        return check

    def _create_invoice_ecom_posted(self):
        if self.invoice_ids:
            return
        saleAdvancePaymentInv = self.env['sale.advance.payment.inv']
        ctx = self.env.context.copy()
        ctx.update({
            'active_ids': [self.id],
            'active_id': self.id
        })
        values = {
            'advance_payment_method': 'delivered',
        }
        payment = saleAdvancePaymentInv.with_context(ctx).create(values)
        payment.create_invoices()
        invoice_id = self.invoice_ids[0]
        invoice_id.action_post()

        return invoice_id

    def do_register_payment(self, invoice_id):
        payments = self.env['account.payment.register'].with_context(active_model='account.move',
                                                                     active_ids=invoice_id.id).create({
            'amount': invoice_id[0].amount_total,
            'group_payment': True,
            'payment_difference_handling': 'open',
            'currency_id': invoice_id[0].currency_id.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
        })._create_payments()

        return payments
