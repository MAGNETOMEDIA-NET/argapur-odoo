from odoo.exceptions import Warning
import json
from woocommerce import API
from odoo import api, fields, models, tools, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)



class AccountMoveLineInherited(models.Model):
    _inherit = "account.move.line"

    product_barcode = fields.Char('Code Barre', related='product_id.barcode', readonly=True)
