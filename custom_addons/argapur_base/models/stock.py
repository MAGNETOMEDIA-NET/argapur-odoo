from odoo.exceptions import Warning
import json
from woocommerce import API
from odoo import api, fields, models, tools, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


wcapi = API(
    url="https://argapur.com/en",
    consumer_key="ck_2931746f6adf193ca9fd1a067e4758829c6dcd73",
    consumer_secret="cs_3a9c56a3cded7ba6615c86887200bd647e0a892b",
    wp_api=True,
    version="wc/v3",
    query_string_auth=True
)

class stockQuantInherited(models.Model):
    _inherit = 'stock.quant'


    def write(self, vals):
        resp = super(stockQuantInherited, self).write(vals)

        if 'reserved_quantity' in vals or 'quantity' in vals:

            if not self.product_id.product_wp_id or self.product_id.product_wp_id == '':
                return resp

            self.available_quantity = self.quantity - self.reserved_quantity

            data = {
                'stock_quantity': self.available_quantity
            }
            res = wcapi.put("products/"+str(self.product_id.product_wp_id), data).json()
            if 'code' in res:
                _logger.info("Something wrong during updating product Quantity")
                _logger.info('Wordpress Api :')
                msg = 'Code : ' + str(res['code'])
                _logger.info(msg)
                msg = 'message : ' + str(res['message'])
                _logger.info(msg)
            else:
                msg = 'the quantity of the product'+self.product_id.name+' est synchronise.'
                _logger.info(msg)
        return resp
