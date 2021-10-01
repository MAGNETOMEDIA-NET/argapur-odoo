# -*- coding: utf-8 -*-
import logging
from odoo.tests import common, Form
from odoo.http import Controller, request, route
_logger = logging.getLogger(__name__)


class WPBaskets(Controller):
    @route(['/web/argapur/create/cmd'], type='json', auth="public", website=False, csrf=False)
    def create_sale_order(self, **kw):
        _logger.info("Start listener to create Sale orders from given WP datas.")
        baskets = request.jsonrequest
        message = 'Basket is empty.'
        res = {"message": message, "created": False}
        if baskets:
            try:
                partner = self._check_partner(baskets)
                if not partner:
                    message = 'The customer does not exist. Cannot create an order without a customer'
                    res = {"message": message, "created": False}
                if partner:
                    if baskets.get('line_items'):
                        order_name, order_id = self._check_items(partner, baskets)
                        _logger.info("END of listener.")
                        message = 'Panier importé avec succès dans Odoo : %s' % order_name
                        res.update({"created": True, "message": message, "id": order_id})
            except Exception as e:
                res.update({"created": False, "message": e})
                return res
        else:
            _logger.info(message)
        return res

    def _check_partner(self, baskets):
        customer = baskets.get('shipping')
        country = request.env['res.country'].sudo().search([('name', '=', customer['country'])])
        partner = request.env['res.partner'].sudo().search([('phone', '=', baskets['billing']['phone'])])
        if partner:
            child_ids_invoice = request.env['res.partner'].sudo().search([('parent_id', '=', partner.id),
                                                                          ('type', '=', 'invoice')])
            child_ids_invoice = self.update_billing_child(customer, child_ids_invoice, country)
            if baskets['customer_id'] == 0:
                customer = baskets.get('shipping')
                child_ids = request.env['res.partner'].sudo().search([('parent_id', '=', partner.id),
                                                                      ('type', '=', 'delivery')])
                child_ids.unlink()
                shipping_childs = self.create_shipping_childs(baskets, partner)
                request.env['res.partner'].sudo().create(shipping_childs)
                partner = self.update_partner(partner, customer, country)
                return partner
            else:
                child_ids_count = request.env['res.partner'].sudo().search_count([('parent_id', '=', partner.id),
                                                                      ('type', '=', 'delivery')])
                if child_ids_count <= 1:
                    shipping_childs = self.create_shipping_childs(baskets, partner)
                    if shipping_childs:
                        request.env['res.partner'].sudo().create(shipping_childs)
                        partner = self.update_partner(partner, customer, country)
                        return partner
                else:
                    child_ids = request.env['res.partner'].sudo().search([('parent_id', '=', partner.id),
                                                                          ('type', '=', 'delivery')], limit=1)
                    child_ids.unlink()
                    shipping_childs = self.create_shipping_childs(baskets, partner)
                    request.env['res.partner'].sudo().create(shipping_childs)
                    partner = self.update_partner(partner, customer, country)
                    return partner
        else:
            name = customer['first_name'] + ' ' + customer['last_name']
            country = request.env['res.country'].sudo().search([('name', '=', customer['country'])])
            partner_values = {
                'type': 'delivery',
                'name': name,
                'phone': baskets['billing']['phone'],
                'email': baskets['billing']['email'],
                'country_id': country.id,
            }
            partner = request.env['res.partner'].sudo().create(partner_values)
            shipping_childs = self.create_shipping_childs(baskets, partner)
            billing_childs = self.create_billing_childs(baskets, partner)
            if shipping_childs:
                request.env['res.partner'].sudo().create(shipping_childs)
            if shipping_childs:
                request.env['res.partner'].sudo().create(billing_childs)
            if partner:
                return partner
            else:
                return False

    def _check_items(self, partner, baskets):
        items = baskets.get('line_items')
        so_lines = []
        for item in items:
            product = self._check_products(item)
            qty = item['quantity']
            price = (float(item['subtotal']) + float(item['subtotal_tax'])) / float(qty)
            self.create_so_line_ecom(so_lines, product, qty, price)
        sale_order = self.create_so_ecom(partner, so_lines, baskets)
        discount = float(baskets['discount_total']) + float(baskets['discount_tax'])
        sale_order.write({
            'discount_rate': discount,
        })
        sale_order.button_dummy()
        try:
            if baskets['shipping_lines'][0]['method_title'] == 'Internationale':
                self.add_shipping_external(sale_order)
        except IndexError:
            pass
        try:
            if baskets['shipping_lines'][0]['method_title'] == 'National':
                self.add_shipping_internal(sale_order)
        except IndexError:
            pass
        sale_order.action_confirm()
        return sale_order.name, sale_order.id

    def create_so_ecom(self, partner, so_lines, baskets):
        payment_method = self._check_payment_method(baskets)
        order_line_ids = []
        order_values = {}
        user = request.env['res.users'].sudo().search([('name', '=', 'Administrator')])
        for element in so_lines:
            order_line_ids.append([0, 0, element])
        order_values.update({
            'partner_id': partner and partner.id,
            'order_line': order_line_ids,
            'payment_method': payment_method.id,
            'user_id': user.id,
            'discount_type': 'amount',
        })
        return request.env['sale.order'].sudo().create(order_values)

    def _check_products(self, item):
        product = request.env['product.product']
        if item.get('name'):
            product = product.sudo().search([('name', '=', item['name'])], limit=1)
        return product

    def create_so_line_ecom(self, so_lines, product, qty, price):
        so_lines_values = {
            'product_id': product and product.id or False,
            'product_uom_qty': qty,
            'price_unit': price,

        }
        return so_lines.append(so_lines_values)

    def create_shipping_childs(self, baskets, partner):
        customer = baskets.get('shipping')
        name = customer['first_name'] + ' ' + customer['last_name']
        shipping_childs = {
            'type': 'delivery',
            'name': name,
            'street': customer['address_1'],
            'parent_id': partner.id,
            'street2': customer['address_2'],
            'city': customer['city'],
            'zip': customer['postcode'],
            'email': baskets['billing']['email'],
        }
        return shipping_childs

    def create_billing_childs(self, baskets, partner):
        customer = baskets.get('shipping')
        name = customer['first_name'] + ' ' + customer['last_name']
        billing_childs = {
            'type': 'invoice',
            'name': name,
            'street': customer['address_1'],
            'parent_id': partner.id,
            'street2': customer['address_2'],
            'city': customer['city'],
            'zip': customer['postcode'],
            'email': baskets['billing']['email'],
        }
        return billing_childs

    def _check_payment_method(self, baskets):

        if baskets['payment_method_title'] == 'CMI':
            payment_method = request.env['account.journal'].sudo().search(
                [('name', '=', 'Carte bancaire')])

        if baskets['payment_method_title'] == 'Virement bancaire':
            payment_method = request.env['account.journal'].sudo().search(
                [('name', '=', 'Virement bancaire')])

        if baskets['payment_method_title'] == 'Paiement à la livraison':
            payment_method = request.env['account.journal'].sudo().search(
                [('name', '=', 'Cash')])

        if baskets['payment_method'] == 'paypal':
            payment_method = request.env['account.journal'].sudo().search(
                [('name', '=', 'Paypal')])

        return payment_method

    def update_partner(self, partner, customer, country):

        partner.street = customer['address_1']
        partner.street2 = customer['address_2']
        partner.city = customer['city']
        partner.country_id = country.id
        partner.zip = customer['postcode']

        return partner

    def update_billing_child(self, customer, child_invoice_id, country):

        child_invoice_id.street = customer['address_1']
        child_invoice_id.street2 = customer['address_2']
        child_invoice_id.city = customer['city']
        child_invoice_id.country_id = country.id
        child_invoice_id.zip = customer['postcode']

        return child_invoice_id

    def add_shipping_internal(self, order):

        product_delivery_normal = request.env['product.product'].sudo().search([('name','=','Argapur_int Delivery Charges')])
        internal_delivery = request.env['delivery.carrier'].sudo().search([('name', '=', 'Internal Delivery Charges')])
        if internal_delivery:
            delivery_wizard = Form(request.env['choose.delivery.carrier'].sudo().with_context({
                'default_order_id': order.id,
                'default_carrier_id': internal_delivery.id
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.button_confirm()

        else:

            internal_delivery = request.env['delivery.carrier'].sudo().create({
                'name': 'Internal Delivery Charges',
                'product_id': product_delivery_normal.id,
                'fixed_price': 40,
                'delivery_type': 'fixed',
            })

            delivery_wizard = Form(request.env['choose.delivery.carrier'].sudo().with_context({
                'default_order_id': order.id,
                'default_carrier_id': internal_delivery.id
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.button_confirm()

    def add_shipping_external(self, order):

        product_delivery_normal = request.env['product.product'].sudo().search([('name','=','Argapur_ext Delivery Charges')])
        external_delivery = request.env['delivery.carrier'].sudo().search([('name', '=', 'External Delivery Charges')])
        if external_delivery:
            delivery_wizard = Form(request.env['choose.delivery.carrier'].sudo().with_context({
                'default_order_id': order.id,
                'default_carrier_id': external_delivery.id
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.button_confirm()

        else:

            external_delivery = request.env['delivery.carrier'].sudo().create({
                'name': 'External Delivery Charges',
                'product_id': product_delivery_normal.id,
                'fixed_price': 312,
                'delivery_type': 'fixed',
            })

            delivery_wizard = Form(request.env['choose.delivery.carrier'].sudo().with_context({
                'default_order_id': order.id,
                'default_carrier_id': external_delivery.id
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.button_confirm()





