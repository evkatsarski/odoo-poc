{
    'name': 'Leather Inspection',
    'version': '20.0.1.0.0',
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
        'quality_control',
        'mrp',
    ],
    'data': [
        'security/leather_inspection_security.xml',
        'security/ir.access.csv',
        'data/decimal_precision.xml',
        'data/ir_sequence.xml',
        'data/product_catalog.xml',
        'views/leather_inspection_views.xml',
        'views/leather_inspection_wizards.xml',
        'views/quality_check_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'leather_inspection/static/tests/tours/leather_inspection_tour.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
