# -*- coding: utf-8 -*-
# (C) 2021 MagnetoMedia

{
    'name': 'ARGAPUR BASE',
    'sequence': 0,
    'version': '14.0.0.0',
    'author': 'MagnetoMedia',
    'license': 'LGPL-3',
    'category': '',
    'description': """
""",
    "author": 'Magnetomedia',
    'website': 'https://www.magnetomedia.de',
    'images': [],
    'depends': [
        'sale_management',
        'stock', 'purchase', 'mrp', 'l10n_ma','sale_discount_total',
    ],
    'data': [
        "data/res_config_settings.xml",
        "data/delivery.xml",
        "data/payment_method.xml",
        "data/taxe.xml",
        'views/product_list_view.xml',
        'views/argapur_settings.xml',
        'views/stock_picking_views_inherited.xml',
        'views/account_move_views_inherited.xml',
        'views/report_invoice_inherited.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'pre_init_hook': 'test_pre_init_hook',

}