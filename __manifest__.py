# -*- coding: utf-8 -*-
{
    'name': 'Supervisión de Arquitectura',
    'version': '15.0',
    'category': 'Tools',
    'summary': 'Plataforma de arquitectura para civiltec',
    'sequence': -100,
    'description': """Module Description""",
    'category': 'Category',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'sr_property_rental_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/quality_form_views.xml',
        'reports/report_checklist_template.xml',
        'reports/report_checklist_action.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
