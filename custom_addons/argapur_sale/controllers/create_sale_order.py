# -*- coding: utf-8 -*-

import logging
from odoo.http import Controller, request, route
_logger = logging.getLogger(__name__)


class WPBaskets(Controller):
    @route(['/web/argapur/create/cmd'], type='json', auth="public", website=False)
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
        customer = baskets.get('billing')
        partner = request.env['res.partner'].sudo().search([('phone', '=', customer['phone'])])
        if partner:
            child_ids = request.env['res.partner'].sudo().search([('parent_id', '=', partner.id),
                                                                  ('type', '=', 'delivery')])
            customer = baskets.get('billing')

            child_ids.street = customer['address_1']
            child_ids.street2 = customer['address_2']
            return partner
        else:
            name = customer['first_name'] + ' ' + customer['last_name']
            country = request.env['res.country'].sudo().search([('name', '=', customer['country'])])
            partner_values = {
                'name': name,
                'phone': customer['phone'],
                'email': customer['email'],
                'country_id': country.id,
            }
            partner = request.env['res.partner'].sudo().create(partner_values)
            shipping_childs = self.create_shipping_childs(baskets, partner)
            if shipping_childs:
                request.env['res.partner'].sudo().create(shipping_childs)
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
            self.create_so_line_ecom(so_lines, product, qty)
        sale_order = self.create_so_ecom(partner, so_lines)
        sale_order.action_confirm()
        return sale_order.name, sale_order.id

    def create_so_ecom(self, partner, so_lines):
        order_line_ids = []
        order_values = {}
        for element in so_lines:
            order_line_ids.append([0, 0, element])
        order_values.update({
            'partner_id': partner and partner.id,
            'order_line': order_line_ids,
        })
        return request.env['sale.order'].sudo().create(order_values)

    def _check_products(self, item):
        product = request.env['product.product']
        if item.get('name'):
            product = product.sudo().search([('name', '=', item['name'])], limit=1)
        return product

    def create_so_line_ecom(self, so_lines, product, qty):
        so_lines_values = {
            'product_id': product and product.id or False,
            'product_uom_qty': qty,
        }
        return so_lines.append(so_lines_values)

    def create_shipping_childs(self, baskets, partner):
        customer = baskets.get('billing')
        name = customer['first_name'] + ' ' + customer['last_name']
        shipping_childs = {
            'type': 'delivery',
            'name': name,
            'street': customer['address_1'],
            'parent_id': partner.id,
            'street2': customer['address_2'],
            'city': customer['city'],
            'zip': customer['postcode'],
        }
        return shipping_childs

