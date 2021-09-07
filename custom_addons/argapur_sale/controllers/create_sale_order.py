# -*- coding: utf-8 -*-

import logging
from odoo.http import Controller, request, route
_logger = logging.getLogger(__name__)


class MagentoBaskets(Controller):
    @route(['/web/argapur/create/cmd'], type='json', auth="public", website=False)
    def create_sale_order(self, **kw):
        _logger.info("Start listener to create Sale orders from given WP datas.")
        baskets = request.jsonrequest
        message = 'Basket is empty.'
        res = {"message": message, "created": False}
        if baskets:
            try:
                if baskets.get('customer_phone'):
                    partner = self._check_partner(baskets.get('customer_phone'))
                    if not partner:
                        message = 'The customer does not exist. Cannot create an order without a customer'
                        res = {"message": message, "created": False}
                if partner:
                    if baskets.get('items'):
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

    def _check_partner(self, customer_phone):
        partner = request.env['res.partner'].sudo().search([('phone', '=', customer_phone)])
        if partner:
            return partner
        else:
            return False

    def _check_items(self, partner, baskets):
        items = baskets.get('items')
        so_lines = []
        for item in items:
            product = self._check_products(item)
            self.create_so_line_ecom(so_lines, product)
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
        if item.get('ean13'):
            product = product.sudo().search([('barcode', '=', item['ean13'])], limit=1)
        return product

    def create_so_line_ecom(self, so_lines, product):
        so_lines_values = {
            'product_id': product and product.id or False,
        }
        return so_lines.append(so_lines_values)

