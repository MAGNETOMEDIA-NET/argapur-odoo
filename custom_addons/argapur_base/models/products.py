from odoo.exceptions import Warning
import json
from woocommerce import API
from odoo import api, fields, models, tools, _, SUPERUSER_ID

wcapi = API(
    url="https://argapur.com",
    consumer_key="ck_6dc4638e541317096bd4bf260bb1edbe543b849c",
    consumer_secret="cs_6ded056384552b0d6cd07691595830e7e663c44b",
    wp_api=True,
    version="wc/v3"
)

class ProducttemplateInherited(models.Model):
    _inherit = "product.template"

    synchronisable = fields.Boolean(string="Synchronisable", default=False)

    def wp_sync(self):
        products_ids = self.env['product.product'].browse(self.env.context.get('active_ids'))
        products_list = []
        for product in products_ids:
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
                msg += 'Code : ' + res['code'] + '\n'
                msg += 'message : ' + res['message'] + '\n'
                res_data = res['data']
                for key, value in res_data['params'].items():
                    msg += key + ' : ' + value + '\n'
                raise Warning(msg)
            else:
                product.write({
                    'barcode': res['id']
                })




