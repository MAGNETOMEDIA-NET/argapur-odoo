from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        res = super(ResUsers, self).create(vals)
        res.write({'lang': 'fr_FR'})
        return res
