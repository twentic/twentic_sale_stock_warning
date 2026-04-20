{
    'name': 'Stock Minimum Warning',
    'version': '18.0.1.0.0',
    'author': 'TwenTIC',
    'website': 'https://www.twentic.com',
    'summary': 'Warns about stock shortages caused by unconfirmed quotations',
    'description': """
        Extends the stock quantity widget in sale order lines to display the quantity
        already reserved in other unconfirmed quotations, adds a yellow warning when
        available stock would be exhausted by those quotations, and notifies the
        salesperson of affected quotations when a competing order is confirmed.
    """,
    'category': 'Sales/Sales',
    'license': 'LGPL-3',
    'depends': ['sale_stock'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'stock_minimum_warning/static/src/widgets/qty_at_date_widget_patch.js',
            'stock_minimum_warning/static/src/widgets/qty_at_date_widget_patch.xml',
            'stock_minimum_warning/static/src/scss/qty_at_date_widget_patch.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
