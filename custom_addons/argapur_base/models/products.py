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
    product_wp_id = fields.Char(string="product ID in Wordpress")


    def show_error_message(self, res):
        msg = 'WordPress API :'
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

    def get_product_qty_available(self):

        stock = self.env['stock.quant'].search([('product_id','=',self.id),('quantity','>=',0)])

        qty_available = stock.quantity - stock.reserved_quantity
        return qty_available

    def synchronise_produits_list_avec_wordpress(self):
        active_ids = self.env.context.get('active_ids', [])
        products_template_ids = self.env['product.template'].browse(active_ids)

        products_list = []
        for product in products_template_ids:
            if not product.synchronisable:
                raise Warning('Le Produit \' '+product.name+'\' n\'est pas synchronisable.')
            elif not product.sale_ok:
                raise Warning('Le Produit \' '+product.name+' \' ne peut pas etre vendu.')
            else:
                products_list.append(product)

        for product in products_list:
            product_qty_available = self.get_product_qty_available()
            data = {
                "name": product.name,
                "type": "simple",
                "regular_price": str(product.list_price),
                "description": product.description,
                "manage_stock": True,
                "stock_quantity": product_qty_available,
                "categories": [],
                "images": []
            }
            if not product.product_wp_id or product.product_wp_id == '':
                res = wcapi.post("products", data).json()
            else:
                res = wcapi.put("products/"+str(product.product_wp_id), data).json()
            if 'code' in res:
                self.show_error_message(res)
            else:
                message = 'Le produit '+ product.name + 'est synchronise avec WordPress'
                _logger.info(message)
                product.write({
                    'product_wp_id': res['id']
                })

    def synchronise_product(self):
        product_qty_available = self.get_product_qty_available()
        data = {
            "name": self.name,
            "type": "simple",
            "regular_price": str(self.list_price),
            "description": self.description,
            "manage_stock": True,
            "stock_quantity": product_qty_available,
            "categories": [],
            "images": []
        }
        if not self.product_wp_id or self.product_wp_id == '':
            res = wcapi.post("products", data).json()
        else:
            res = wcapi.put("products/"+str(self.product_wp_id), data).json()
        if 'code' in res:
            self.show_error_message(res)
        self.write({
            'product_wp_id' : res['id']
        })

    def synchronise_product_price(self):
        if not self.synchronisable:
            raise Warning('Ce Produit n\'est pas synchronisable.')

        if not self.product_wp_id or self.product_wp_id == '':
            raise Warning('Ce Produit n\'est pas encore synchronise avec WordPress.')
        product_wp_id = self.product_wp_id
        res = wcapi.get("products/"+str(product_wp_id)).json()
        if 'code' in res:
            self.show_error_message(res)
        else:
            wp_product_price = res['regular_price']
            if float(wp_product_price) == float(self.list_price):
                raise Warning('Le prix de ce Produit est a jour avec WordPress (Rien a modifier).')

            data = {
                "regular_price": str(self.list_price)
            }
            res = wcapi.put("products/"+str(product_wp_id), data).json()
            if 'code' in res:
                self.show_error_message(res)
            else:
                raise Warning('Le prix de ce Produit est synchronise avec succès.')