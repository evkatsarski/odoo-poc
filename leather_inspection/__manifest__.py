{
    'name': 'Leather Inspection',
    'version': '20.0.1.1.0',
    'category': 'Supply Chain/Quality',
    'summary': 'Incoming leather lot inspection for a luxury leather-goods workshop',
    'description': """
Incoming leather inspection that stays beside standard Odoo Quality, Inventory,
and Manufacturing. Inspection actions record measurements only. They do not
post stock, rewrite lot quantities, consume leather, or pass the quality check.
    """,
    'author': 'Leather Inspection Prototype',
    'license': 'LGPL-3',
    'depends': [
        'web',
        'quality_control',
        'mrp',
    ],
    'data': [
        'security/leather_inspection_security.xml',
        'security/ir.access.csv',
        'data/decimal_precision.xml',
        'data/ir_sequence.xml',
        'data/product_catalog.xml',
        'data/kroy_brand.xml',
        'views/kroy_login_templates.xml',
        'views/leather_inspection_views.xml',
        'views/leather_inspection_wizards.xml',
        'views/quality_check_views.xml',
        'views/menus.xml',
        'data/language.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'leather_inspection/static/src/scss/kroy_primary_variables.scss'),
        ],
        'web.assets_backend': [
            'leather_inspection/static/src/scss/kroy_brand.scss',
            'leather_inspection/static/src/xml/navbar.xml',
        ],
        'web.assets_frontend': [
            'leather_inspection/static/src/scss/kroy_brand.scss',
        ],
        'web.assets_tests': [
            'leather_inspection/static/tests/tours/leather_inspection_tour.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
