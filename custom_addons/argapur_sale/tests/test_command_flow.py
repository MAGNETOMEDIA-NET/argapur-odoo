from odoo.tests.common import TransactionCase
from odoo.tests.common import SavepointCase
from odoo.exceptions import UserError


class TestCommandFlow(TransactionCase):

    def setUp(self):
        super().setUp()
        # admin_user = self.env.ref('base.user_admin')
        self.order = self.env['sale.order']
        self.a_client = self.env['res.partner'].create({
            'company_type': 'person',
            'name': 'Jhon'
        })
        self.a_product_1 = self.env['product.template'].create({
            'name': 'Product 1',
            'sale_ok': True,
            'type': 'product',
        })
        self.a_product_2 = self.env['product.template'].create({
            'name': 'Product 2',
            'sale_ok': True,
            'type': 'product',
        })
        location = self.env['stock.location'].sudo().search([('complete_name','=','WH/Stock')])
        self.a_stock = self.env['stock.quant'].create({
            'product_id': self.a_product_1.id,
            'location_id': location.id,
            'quantity': 100,
        })
        self.a_stock = self.env['stock.quant'].create({
            'product_id': self.a_product_2.id,
            'location_id': location.id,
            'quantity': 10,
        })

        self.payment_method_cmi = self.env['account.journal'].sudo().search(
            [('name', '=', 'Carte bancaire')])
        self.payment_method_paypal = self.env['account.journal'].sudo().search(
            [('name', '=', 'Paypal')])
        self.payment_method_cash = self.env['account.journal'].sudo().search(
                    [('name', '=', 'Cash')])

    def test_check_availability(self):

        so_lines_1 = [{
            'product_id': self.a_product_1.id,
            'product_uom_qty': 5,
        }]
        so_lines_2 = [{
            'product_id': self.a_product_2.id,
            'product_uom_qty': 15,
        }]

        order_line_ids_1 = []
        for element in so_lines_1:
            order_line_ids_1.append([0, 0, element])

        so_1 = self.order.create({
            'partner_id': self.a_client.id,
            'order_line': order_line_ids_1,
        })

        order_line_ids_2 = []
        for element in so_lines_2:
            order_line_ids_2.append([0, 0, element])

        so_2 = self.order.create({
            'partner_id': self.a_client.id,
            'order_line': order_line_ids_2,
        })

        res_1 = so_1.check_availability(so_1)
        res_2 = so_2.check_availability(so_2)

        self.assertEqual(res_1, True)
        self.assertEqual(res_2, False)

    def test_action_confirm(self):

        # Test CMI and quantity available
        so_lines = [{
            'product_id': self.a_product_1.id,
            'product_uom_qty': 5,
        }]

        order_line_ids = []
        for element in so_lines:
            order_line_ids.append([0, 0, element])

        so = self.order.create({
            'partner_id': self.a_client.id,
            'order_line': order_line_ids,
            'payment_method': self.payment_method_cmi.id,
        })
        so.action_confirm()
        mail_sent = so.invoice_ids.is_move_sent
        invoice_paid = so.invoice_ids.payment_state
        pick_state = []
        pick_state_cmi = ['assigned', 'done']
        for p in so.picking_ids:
            pick_state.append(p.state)

        self.assertTrue(mail_sent, msg='CMI/available mail not sent')
        self.assertEqual(invoice_paid, 'paid', msg='CMI/available invoice not paid')
        self.assertEqual(pick_state, pick_state_cmi, msg='CMI/available pick not done')

        # Test Paypal and quantity available
        so_lines = [{
            'product_id': self.a_product_1.id,
            'product_uom_qty': 5,
        }]

        order_line_ids = []
        for element in so_lines:
            order_line_ids.append([0, 0, element])

        so = self.order.create({
            'partner_id': self.a_client.id,
            'order_line': order_line_ids,
            'payment_method': self.payment_method_paypal.id,
        })
        so.action_confirm()
        mail_sent = so.invoice_ids.is_move_sent
        invoice_paid = so.invoice_ids.payment_state
        pick_state = []
        pick_state_paypal = ['assigned', 'done']
        for p in so.picking_ids:
            pick_state.append(p.state)

        self.assertTrue(mail_sent, msg='Paypal/available mail not sent')
        self.assertEqual(invoice_paid, 'paid', msg='Paypal/available invoice not paid')
        self.assertEqual(pick_state, pick_state_paypal, msg='Paypal/available pick not done')

        # Test Paypal and quantity not available
        so_lines = [{
            'product_id': self.a_product_1.id,
            'product_uom_qty': 5,
        }, {
            'product_id': self.a_product_2.id,
            'product_uom_qty': 15,
        }]

        order_line_ids = []
        for element in so_lines:
            order_line_ids.append([0, 0, element])

        so = self.order.create({
            'partner_id': self.a_client.id,
            'order_line': order_line_ids,
            'payment_method': self.payment_method_paypal.id,
        })
        so.action_confirm()
        mail_sent = so.invoice_ids.is_move_sent
        invoice_paid = so.invoice_ids.payment_state
        pick_state = []
        pick_state_not_avail = ['waiting', 'assigned']
        for p in so.picking_ids:
            pick_state.append(p.state)

        self.assertTrue(mail_sent, msg='Paypal/not_available mail not sent')
        self.assertEqual(invoice_paid, 'paid', msg='Paypal/not_available invoice not paid')
        self.assertEqual(pick_state, pick_state_not_avail, msg='Paypal/not_available pick not done')

        # Test Cash and quantity available
        so_lines = [{
            'product_id': self.a_product_1.id,
            'product_uom_qty': 5,
        }]

        order_line_ids = []
        for element in so_lines:
            order_line_ids.append([0, 0, element])

        so = self.order.create({
            'partner_id': self.a_client.id,
            'order_line': order_line_ids,
            'payment_method': self.payment_method_cash.id,
        })
        so.action_confirm()
        mail_sent = so.invoice_ids.is_move_sent
        invoice_paid = so.invoice_ids.payment_state
        pick_state = []
        pick_state_cash = ['assigned', 'done']
        for p in so.picking_ids:
            pick_state.append(p.state)

        self.assertTrue(mail_sent, msg='Cash/available mail not sent')
        self.assertEqual(invoice_paid, 'not_paid', msg='Cash/available invoice not paid')
        self.assertEqual(pick_state, pick_state_cash, msg='Cash/available pick not done')

        # Test Cash and quantity not available
        so_lines = [{
            'product_id': self.a_product_1.id,
            'product_uom_qty': 5,
        }, {
            'product_id': self.a_product_2.id,
            'product_uom_qty': 15,
        }]

        order_line_ids = []
        for element in so_lines:
            order_line_ids.append([0, 0, element])

        so = self.order.create({
            'partner_id': self.a_client.id,
            'order_line': order_line_ids,
            'payment_method': self.payment_method_cash.id,
        })
        so.action_confirm()
        mail_sent = so.invoice_ids.is_move_sent
        invoice_paid = so.invoice_ids.payment_state
        pick_state = []
        pick_state_not_avail = ['waiting', 'assigned']
        for p in so.picking_ids:
            pick_state.append(p.state)

        self.assertTrue(mail_sent, msg='Cash/not_available mail not sent')
        self.assertEqual(invoice_paid, 'not_paid', msg='Cash/not_available invoice not paid')
        self.assertEqual(pick_state, pick_state_not_avail, msg='Cash/not_available pick not done')

