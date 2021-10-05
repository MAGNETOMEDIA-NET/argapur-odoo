from odoo import api, fields, models


class ArgapurSetting(models.TransientModel):

    _inherit = 'res.config.settings'
    _description = 'Settings'

    website_url = fields.Char(string="The Website Url")
    consumer_key = fields.Char(string="Consumer Key")
    consumer_secret = fields.Char(string="Consumer Secret")

    user = fields.Char(string="User")
    password = fields.Char(string="Password")

    def set_values(self):
        res = super(ArgapurSetting, self).set_values()

        self.env['ir.config_parameter'].set_param('argapur_base.website_url', self.website_url)

        self.env['ir.config_parameter'].set_param('argapur_base.consumer_key', self.consumer_key)
        self.env['ir.config_parameter'].set_param('argapur_base.consumer_secret', self.consumer_secret)

        self.env['ir.config_parameter'].set_param('argapur_base.user', self.user)
        self.env['ir.config_parameter'].set_param('argapur_base.password', self.password)

    @api.model
    def get_values(self):
        res = super(ArgapurSetting, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        website_url = ICPSudo.get_param('argapur_base.website_url')
        res.update(website_url=website_url)

        consumer_key = ICPSudo.get_param('argapur_base.consumer_key')
        res.update(consumer_key=consumer_key)
        consumer_secret = ICPSudo.get_param('argapur_base.consumer_secret')
        res.update(consumer_secret=consumer_secret)

        user = ICPSudo.get_param('argapur_base.user')
        res.update(user=user)
        password = ICPSudo.get_param('argapur_base.password')
        res.update(password=password)

        return res