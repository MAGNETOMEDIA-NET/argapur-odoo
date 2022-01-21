from odoo.exceptions import Warning
import json
from woocommerce import API
from odoo import api, fields, models, tools, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)



class stockMoveInherited(models.Model):
    _inherit = "stock.move"

    product_barcode = fields.Char('Code Barre', related='product_id.barcode', readonly=True)
