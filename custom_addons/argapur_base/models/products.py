from odoo.exceptions import Warning
import json
from woocommerce import API
from odoo import api, fields, models, tools, _, SUPERUSER_ID

import requests
import base64
import shutil
import os



import logging

_logger = logging.getLogger(__name__)

wcapi_old = API(
    url="https://argapur.com/en",
    consumer_key="ck_2931746f6adf193ca9fd1a067e4758829c6dcd73",
    consumer_secret="cs_3a9c56a3cded7ba6615c86887200bd647e0a892b",
    wp_api=True,
    version="wc/v3",
    timeout=99,
    query_string_auth=True
)

##### (Application Password) Api params
app_pass_endpoint_old = "https://argapur.com/en/wp-json/wp/v2"
app_pass_user_old = 'mehdi'
app_pass_password_old = 'yLaW Ptsu c7pY 0hlt RnFG bDAc'


class ProducttemplateInherited(models.Model):
    _inherit = "product.template"

    produit_fini = fields.Boolean(string="Produit Fini", default=False)
    synchronise = fields.Boolean(string="Synchronisé", default=False)
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
            raise Warning('Ce Produit ne peut pas être un Produit Fini.\n'
                          'Message : il n\'est pas stockable (Storable).')

        # check Route if 'Manufacturing'
        location_route = self.env['stock.location.route'].search([('name', 'in', ['Produire','Manufacture'])], limit=1)
        if location_route not in self.route_ids:
            raise Warning('Ce Produit ne peut pas être un Produit Fini.\n'
                          'Message : il n\'a pas de voie de fabrication (Manufacturing route).')

        # check Nomenclature
        mrp_bom = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.id)])
        if not mrp_bom:
            raise Warning('Ce Produit ne peut pas être un Produit Fini.\n'
                          'Message : il n\'a pas Nomenclature (Bill of Materials).')

        # check regles d'approvisionnement
        orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product.id)])
        if not orderpoint:
            raise Warning('Ce Produit ne peut pas être un Produit Fini\n'
                          'Message : il n\'a pas des regles d\'approvisionnement (Recordering Rules).')

        return resp


    # ************************ Check and show Woocommerce api message error
    def show_error_message(self, res):
        msg = 'Woocommerce API :\n'
        msg += 'Code : ' + str(res['code']) + '\n'
        msg += 'Message : ' + str(res['message']) + '\n'
        res_data = res['data']
        if 'params' in res_data:
            for key, value in res_data['params'].items():
                msg += str(key) + ' : ' + str(value) + '\n'
        else:
            for key, value in res_data.items():
                msg += str(key) + ' : ' + str(value) + '\n'
        raise Warning(msg)

    def check_response_code(self, res):
        if res.status_code == 400:
            raise Warning('Problème de Woocommerce API.\n'
                          '(400) Bad Request : Invalid request, e.g. using an unsupported HTTP method.')
        if res.status_code == 401:
            raise Warning('Problème de Woocommerce API.\n'
                          '(401) Unauthorized : Authentication or permission error, e.g. incorrect API keys.')
        if res.status_code == 404:
            raise Warning('Problème de Woocommerce API.\n'
                          '(404) Not Found : Requests to resources that don\'t exist or are missing.')
        if res.status_code == 500:
            raise Warning('Problème de Woocommerce APi.\n'
                          '(500) Internal Server Error : Server error.')


    # ************************ Check and show Application Password api message error
    def show_error_message_app_pass(self, res):
        msg = 'Application Password API :\n'
        msg += 'Code : ' + str(res['code']) + '\n'
        msg += 'Message : ' + str(res['message']) + '\n'
        res_data = res['data']
        if 'params' in res_data:
            for key, value in res_data['params'].items():
                msg += str(key) + ' : ' + str(value) + '\n'
        else:
            for key, value in res_data.items():
                msg += str(key) + ' : ' + str(value) + '\n'
        raise Warning(msg)

    def check_response_code_app_pass(self, res):
        if res.status_code == 400:
            raise Warning('Problème de Application Password API.\n'
                          '(400) Bad Request : Invalid request, e.g. using an unsupported HTTP method.')
        if res.status_code == 401:
            raise Warning('Problème de Application Password API.\n'
                          '(401) Unauthorized : Authentication or permission error, e.g. incorrect API keys.')
        if res.status_code == 404:
            raise Warning('Problème de Application Password API.\n'
                          '(404) Not Found : Requests to resources that don\'t exist or are missing.')
        if res.status_code == 500:
            raise Warning('Problème de Application Password API.\n'
                          '(500) Internal Server Error : Server error.')

    # *********************************************************************************
    # *********************************************************************************

    def get_product_qty_available(self):
        product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.id)]).id
        stock = self.env['stock.quant'].search([('product_id', '=', product_id), ('location_id.name', '=', 'STOCK SITE WEB')])
        qty_available = stock.quantity - stock.reserved_quantity
        return qty_available

    def synchronise_product(self):

        website_url = self.env['ir.config_parameter'].sudo().get_param('argapur_base.website_url')

        consumer_key = self.env['ir.config_parameter'].sudo().get_param('argapur_base.consumer_key')
        consumer_secret = self.env['ir.config_parameter'].sudo().get_param('argapur_base.consumer_secret')

        user = self.env['ir.config_parameter'].sudo().get_param('argapur_base.user')
        password = self.env['ir.config_parameter'].sudo().get_param('argapur_base.password')

        if not website_url:
            raise Warning('Veuillez remplire le champ Website_url dans Configuration/Argapur !')

        if not consumer_key:
            raise Warning('Veuillez remplire le champ consumer_key dans Configuration/Argapur !')
        if not consumer_secret:
            raise Warning('Veuillez remplire le champ consumer_secret dans Configuration/Argapur !')

        if not user:
            raise Warning('Veuillez remplire le champ user dans Configuration/Argapur !')
        if not password:
            raise Warning('Veuillez remplire le champ password dans Configuration/Argapur !')

        ## Woocommerce API
        wcapi = API(
            url=website_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            wp_api=True,
            version="wc/v3",
            timeout=99,
            query_string_auth=True
        )

        ## Application Password Creds
        app_pass_endpoint = str(website_url) + "/wp-json/wp/v2"
        app_pass_user = user
        app_pass_password = password


        # **************************************************************************
        # **************************************************************************


        product_qty_available = self.get_product_qty_available()

        attach = self.env['ir.attachment'].search(
            [('res_model', '=', 'product.template'), ('res_id', '=', self.id), ('res_field', '=', "image_1920")])
        images = []
        image_id = False
        old_image_id = False
        if attach:
            image_path = r''+str(attach._full_path(attach.store_fname))
            image_dst = r''+str(image_path)+'.png'
            shutil.copyfile(image_path, image_dst)
            creds = app_pass_user + ':' + app_pass_password
            token = base64.b64encode(creds.encode())
            header = {'Authorization': 'Basic ' + token.decode('utf-8')}
            media = {
                'file': open(image_dst, 'rb'),
            }
            response = requests.request(
                "POST", app_pass_endpoint + "/media", headers=header,
                files=media,
                auth=(app_pass_user, app_pass_password)
            )
            if response.headers.get('content-type').split(';')[0] != 'application/json':
                self.check_response_code_app_pass(response)
            json_res = response.json()
            if 'code' in json_res:
                self.show_error_message_app_pass(json_res)
            image_id = json_res['id']
            images = [
                {
                    'id' : image_id
                }
            ]
            os.remove(image_dst)

        data = {
            "name": self.name,
            "type": "simple",
            "regular_price": str(self.list_price),
            "description": self.description,
            "manage_stock": True,
            "stock_quantity": product_qty_available,
            "categories": [],
            "images": images
        }
        if not self.product_wp_id or self.product_wp_id == "":
            res = wcapi.post("products", data)
            if res.headers.get('content-type').split(';')[0] != 'application/json':
                if image_id:
                    response = requests.request(
                        "DELETE",  app_pass_endpoint + "/media/"+str(image_id)+"?force=true", headers=header,
                        auth=(app_pass_user, app_pass_password)
                    )

                self.check_response_code(res)
            res = res.json()
        else:
            if image_id:
                res = wcapi.get("products/"+str(self.product_wp_id))
                if res.headers.get('content-type').split(';')[0] != 'application/json':
                    response = requests.request(
                        "DELETE", app_pass_endpoint + "/media/" + str(image_id) + "?force=true", headers=header,
                        auth=(app_pass_user, app_pass_password)
                    )
                    self.check_response_code(res)
                res = res.json()
                if 'code' in res:
                    response = requests.request(
                        "DELETE", app_pass_endpoint + "/media/" + str(image_id) + "?force=true", headers=header,
                        auth=(app_pass_user, app_pass_password)
                    )
                product_images = res['images']
                if product_images:
                    old_image_id = product_images[0]['id']

            res = wcapi.put("products/" + str(self.product_wp_id), data)
            if res.headers.get('content-type').split(';')[0] != 'application/json':
                if image_id:
                    response = requests.request(
                        "DELETE",  app_pass_endpoint + "/media/"+str(image_id)+"?force=true", headers=header,
                        auth=(app_pass_user, app_pass_password)
                    )
                self.check_response_code(res)
            res = res.json()
        if 'code' in res:
            if image_id:
                response = requests.request(
                    "DELETE", app_pass_endpoint + "/media/" + str(image_id) + "?force=true", headers=header,
                    auth=(app_pass_user, app_pass_password)
                )
            self.show_error_message(res)
        if old_image_id:
            response = requests.request(
                "DELETE", app_pass_endpoint + "/media/" + str(old_image_id) + "?force=true", headers=header,
                auth=(app_pass_user, app_pass_password)
            )
        self.write({
            'synchronise': True,
            'product_wp_id': res['id']
        })

    def synchronise_produits_list_avec_wordpress(self):
        website_url = self.env['ir.config_parameter'].sudo().get_param('argapur_base.website_url')

        consumer_key = self.env['ir.config_parameter'].sudo().get_param('argapur_base.consumer_key')
        consumer_secret = self.env['ir.config_parameter'].sudo().get_param('argapur_base.consumer_secret')

        user = self.env['ir.config_parameter'].sudo().get_param('argapur_base.user')
        password = self.env['ir.config_parameter'].sudo().get_param('argapur_base.password')

        if not website_url:
            raise Warning('Veuillez remplire le champ Website_url dans Configuration/Argapur !')

        if not consumer_key:
            raise Warning('Veuillez remplire le champ consumer_key dans Configuration/Argapur !')
        if not consumer_secret:
            raise Warning('Veuillez remplire le champ consumer_secret dans Configuration/Argapur !')

        if not user:
            raise Warning('Veuillez remplire le champ user dans Configuration/Argapur !')
        if not password:
            raise Warning('Veuillez remplire le champ password dans Configuration/Argapur !')

        ## Woocommerce API
        wcapi = API(
            url=website_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            wp_api=True,
            version="wc/v3",
            timeout=99,
            query_string_auth=True
        )

        ## Application Password Creds
        app_pass_endpoint = str(website_url) + "/wp-json/wp/v2"
        app_pass_user = user
        app_pass_password = password
        # **********************************************************************************
        # **********************************************************************************

        active_ids = self.env.context.get('active_ids', [])
        products_template_ids = self.env['product.template'].browse(active_ids)

        products_list = []
        for product in products_template_ids:
            if not product.present_sur_site:
                raise Warning('Le Produit \' ' + product.name + ' \' n\'est pas present sur site.')
            else:
                products_list.append(product)

        for product in products_list:
            attach = self.env['ir.attachment'].search(
                [('res_model', '=', 'product.template'), ('res_id', '=', product.id), ('res_field', '=', "image_1920")])

            images = []
            image_id = False
            old_image_id = False
            if attach:
                image_path = r'' + str(attach._full_path(attach.store_fname))
                image_dst = r'' + str(image_path) + '.png'
                shutil.copyfile(image_path, image_dst)
                creds = app_pass_user + ':' + app_pass_password
                token = base64.b64encode(creds.encode())
                header = {'Authorization': 'Basic ' + token.decode('utf-8')}
                media = {
                    'file': open(image_dst, 'rb'),
                }
                response = requests.request(
                    "POST", app_pass_endpoint + "/media", headers=header,
                    files=media,
                    auth=(app_pass_user, app_pass_password)
                )
                if response.headers.get('content-type').split(';')[0] != 'application/json':
                    self.check_response_code_app_pass(response)
                json_res = response.json()
                image_id = json_res['id']
                if 'code' in json_res:
                    self.show_error_message_app_pass(json_res)
                images = [
                    {
                        'id': image_id
                    }
                ]
                os.remove(image_dst)

            product_id = self.env['product.product'].search([('product_tmpl_id', '=', product.id)]).id
            stock = self.env['stock.quant'].search(
                [('product_id', '=', product_id), ('location_id.name', '=', 'STOCK SITE WEB')])
            product_qty_available = stock.quantity - stock.reserved_quantity
            data = {
                "name": product.name,
                "type": "simple",
                "regular_price": str(product.list_price),
                "description": product.description,
                "manage_stock": True,
                "stock_quantity": product_qty_available,
                "categories": [],
                "images": images
            }
            if not product.product_wp_id or product.product_wp_id== "":
                res = wcapi.post("products", data)
                if res.headers.get('content-type').split(';')[0] != 'application/json':
                    if image_id:
                        response = requests.request(
                            "DELETE", app_pass_endpoint + "/media/" + str(image_id) + "?force=true", headers=header,
                            auth=(app_pass_user, app_pass_password)
                        )
                    self.check_response_code(self, res)
                res = res.json()
            else:
                if image_id:
                    res = wcapi.get("products/"+str(product.product_wp_id))
                    if res.headers.get('content-type').split(';')[0] != 'application/json':
                        response = requests.request(
                            "DELETE", app_pass_endpoint + "/media/" + str(image_id) + "?force=true", headers=header,
                            auth=(app_pass_user, app_pass_password)
                        )
                        self.check_response_code(res)
                    res = res.json()
                    if 'code' in res:
                        response = requests.request(
                            "DELETE", app_pass_endpoint + "/media/" + str(image_id) + "?force=true", headers=header,
                            auth=(app_pass_user, app_pass_password)
                        )
                    product_images = res['images']
                    if product_images:
                        old_image_id = product_images[0]['id']

                res = wcapi.put("products/" + str(product.product_wp_id), data)
                if res.headers.get('content-type').split(';')[0] != 'application/json':
                    if image_id:
                        response = requests.request(
                            "DELETE", app_pass_endpoint + "/media/" + str(image_id) + "?force=true", headers=header,
                            auth=(app_pass_user, app_pass_password)
                        )
                    self.check_response_code(self, res)
                res = res.json()
            if 'code' in res:
                if image_id:
                    response = requests.request(
                        "DELETE",  app_pass_endpoint + "/media/"+str(image_id)+"?force=true", headers=header,
                        auth=(app_pass_user, app_pass_password)
                    )
                self.show_error_message(res)
            else:
                if old_image_id:
                    response = requests.request(
                        "DELETE", app_pass_endpoint + "/media/" + str(old_image_id) + "?force=true", headers=header,
                        auth=(app_pass_user, app_pass_password)
                    )
                message = 'Le produit ' + product.name + 'est synchronise avec WordPress.'
                _logger.info(message)
                product.write({
                    'synchronise': True,
                    'product_wp_id': res['id']
                })


    def synchronise_product_price(self):
        website_url = self.env['ir.config_parameter'].sudo().get_param('argapur_base.website_url')

        consumer_key = self.env['ir.config_parameter'].sudo().get_param('argapur_base.consumer_key')
        consumer_secret = self.env['ir.config_parameter'].sudo().get_param('argapur_base.consumer_secret')

        user = self.env['ir.config_parameter'].sudo().get_param('argapur_base.user')
        password = self.env['ir.config_parameter'].sudo().get_param('argapur_base.password')

        if not website_url:
            raise Warning('Veuillez remplire le champ Website_url dans Configuration/Argapur !')

        if not consumer_key:
            raise Warning('Veuillez remplire le champ consumer_key dans Configuration/Argapur !')
        if not consumer_secret:
            raise Warning('Veuillez remplire le champ consumer_secret dans Configuration/Argapur !')

        if not user:
            raise Warning('Veuillez remplire le champ user dans Configuration/Argapur !')
        if not password:
            raise Warning('Veuillez remplire le champ password dans Configuration/Argapur !')

        ## Woocommerce API
        wcapi = API(
            url=website_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            wp_api=True,
            version="wc/v3",
            timeout=99,
            query_string_auth=True
        )

        product_wp_id = self.product_wp_id
        res = wcapi.get("products/" + str(product_wp_id))
        if res.headers.get('content-type').split(';')[0] != 'application/json':
            self.check_response_code(self, res)
        res = res.json()
        if 'code' in res:
            self.show_error_message(res)
        else:
            wp_product_price = res['regular_price']
            if float(wp_product_price) == float(self.list_price):
                raise Warning('Le prix de ce Produit est a jour avec WordPress.')

            data = {
                "regular_price": str(self.list_price)
            }
            res = wcapi.put("products/" + str(product_wp_id), data)
            if res.headers.get('content-type').split(';')[0] != 'application/json':
                self.check_response_code(self, res)
            res = res.json()

            if 'code' in res:
                self.show_error_message(res)
            else:
                raise Warning('Le prix de ce Produit est synchronise avec succès.')
