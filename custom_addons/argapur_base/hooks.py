from odoo import api, SUPERUSER_ID


def test_pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    fr = env['res.lang'].sudo().search([('code', '=', 'fr_FR'), ('active', 'in', [True, False])], limit=1)
    fr.sudo().write({'active': True})
    users = env['res.users'].sudo().search([])
    for user in users:
        user.sudo().write({
            'lang': 'fr_FR',
        })
