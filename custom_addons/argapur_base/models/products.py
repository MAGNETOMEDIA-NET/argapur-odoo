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

class ProducttemplateInherited(models.Model):
    _inherit = "product.template"

    synchronisable = fields.Boolean(string="Synchronisable", default=False)

    def synchronise_produits_list_avec_wordpress(self):
        active_ids = self.env.context.get('active_ids', [])
        _logger.warning(active_ids)
        products_template_ids = self.env['product.template'].browse(active_ids)
        _logger.warning(products_template_ids)

        products_list = []
        for product in products_template_ids:
            if not product.synchronisable:
                raise Warning('Le Produit \' '+product.name+'\' n\'est pas synchronisable.')
            elif product.barcode:
                raise Warning('Le Produit \' '+product.name+'\' est déjà synchronise.')
            else:
                products_list.append(product)

        for product in products_list:
            data = {
                "name": product.name,
                "type": "simple",
                "regular_price": str(product.list_price),
                "description": product.description,
                "categories": [],
                "images": []
            }
            res = wcapi.post("products", data).json()
            if 'code' in res:
                msg = 'Le Produit ( ' + product.name + ' ) n\' est pas créé sous Wordpress \n'
                msg += 'Code : ' + str(res['code']) + '\n'
                msg += 'message : ' + str(res['message']) + '\n'
                res_data = res['data']

                if 'params' in res_data:
                    for key, value in res_data['params'].items():
                        msg += str(key) + ' : ' + str(value) + '\n'
                else:
                    for key, value in res_data.items():
                        msg += str(key) + ' : ' + str(value) + '\n'
                raise Warning(msg)
            else:
                product.write({
                    'barcode': res['id']
                })




