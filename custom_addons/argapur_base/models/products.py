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

    produit_fini = fields.Boolean(string="Produit Fini", default=False)
    synchronise = fields.Boolean(string="Synchronisé", default=False, readonly=True)
    product_wp_id = fields.Char(string="product ID in Wordpress", default="")
    present_sur_site = fields.Boolean(string="Présent sur Site", default=False)

    @api.model
    def create(self, vals):

        if 'produit_fini' in vals:
            if vals['produit_fini']:
                raise Warning('Vous ne pouvez pas créer un Produit Fini sans ajouter les informations nécessaires :\n'
                              '+ Nomenclature \n'
                              '+ Régle d \'approvisionnement.')
        if 'present_sur_site' in vals:
            if vals['present_sur_site']:
                vals["sale_ok"] = True

        resp = super(ProducttemplateInherited, self).create(vals)
        return resp

    def write(self, vals):
        if 'present_sur_site' in vals:
            if vals['present_sur_site']:
                vals["sale_ok"] = True
        elif self.present_sur_site:
            vals["sale_ok"] = True
        resp = super(ProducttemplateInherited, self).write(vals)
        if 'produit_fini' not in vals:
            return resp
        elif not vals['produit_fini']:
            return resp
        product = self.env['product.product'].search([('product_tmpl_id', '=', self.id)])
        # check if stockable
        if self.type != 'product':
            raise Warning('Ce Produit ne peut pas être un Produit Fini:\n'
                          'message : il n\'est pas stockable (Storable).')

        # check Route if 'Manufacturing'
        location_route = self.env['stock.location.route'].search([('name', 'in', ['Produire', 'Manufacture'])], limit=1)
        if location_route not in self.route_ids:
            raise Warning('Ce Produit ne peut pas être un Produit Fini : \n'
                          'message : il n\'a pas de voie de fabrication (Manufacturing route).')

        # check Nomenclature
        mrp_bom = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.id)])
        if not mrp_bom:
            raise Warning('Ce Produit ne peut pas être un Produit Fini :\n'
                          'message : il n\'a pas Nomenclature (Bill of Materials).')

        # check regles d'approvisionnement
        orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product.id)])
        if not orderpoint:
            raise Warning('Ce Produit ne peut pas être un Produit Fini: \n'
                          'message : il n\'a pas des regles d\'approvisionnement (Recordering Rules).')

        return resp


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
        product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.id)]).id
        stock = self.env['stock.quant'].search([('product_id', '=', product_id), ('location_id.name', '=', 'Stock')])
        qty_available = stock.quantity - stock.reserved_quantity
        return qty_available


    def synchronise_produits_list_avec_wordpress(self):
        active_ids = self.env.context.get('active_ids', [])
        products_template_ids = self.env['product.template'].browse(active_ids)

        products_list = []
        for product in products_template_ids:
            if not product.present_sur_site:
                raise Warning('Le Produit \' ' + product.name + ' \' est pas present sur site.')
            else:
                products_list.append(product)

        for product in products_list:
            product_id = self.env['product.product'].search([('product_tmpl_id', '=', product.id)]).id
            stock = self.env['stock.quant'].search(
                [('product_id', '=', product_id), ('location_id.name', '=', 'Stock')])
            product_qty_available = stock.quantity - stock.reserved_quantity
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
            if not product.synchronise:
                res = wcapi.post("products", data).json()
            else:
                res = wcapi.put("products/" + str(product.product_wp_id), data).json()
            if 'code' in res:
                self.show_error_message(res)
            else:
                message = 'Le produit ' + product.name + 'est synchronise avec WordPress'
                _logger.info(message)
                product.write({
                    'synchronise': True,
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
        if not self.synchronise:
            res = wcapi.post("products", data).json()
        else:
            res = wcapi.put("products/" + str(self.product_wp_id), data).json()
        if 'code' in res:
            self.show_error_message(res)
        self.write({
            'synchronise': True,
            'product_wp_id': res['id']
        })


    def synchronise_product_price(self):
        product_wp_id = self.product_wp_id
        res = wcapi.get("products/" + str(product_wp_id)).json()
        if 'code' in res:
            self.show_error_message(res)
        else:
            wp_product_price = res['regular_price']
            if float(wp_product_price) == float(self.list_price):
                raise Warning('Le prix de ce Produit est a jour avec WordPress.')

            data = {
                "regular_price": str(self.list_price)
            }
            res = wcapi.put("products/" + str(product_wp_id), data).json()
            if 'code' in res:
                self.show_error_message(res)
            else:
                raise Warning('Le prix de ce Produit est synchronise avec succès.')
