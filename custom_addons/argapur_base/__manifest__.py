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
        'stock', 'purchase', 'mrp', 'l10n_ma',
    ],
    'data': [
        'views/product_list_view.xml',
        "data/res_config_settings.xml",
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}