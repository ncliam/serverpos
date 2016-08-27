# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'NC POS',
    'version': '1.0.1',
    'category': 'Point Of Sale',
    'sequence': 6,
    'summary': 'Support external Android POS',
    'description': """

Sync data from Mobility
===========================

This module allows you to sync data with mobility POS. 

Main Features
-------------
* Register new business account (initial company, posconfig, journal)
* Listen to new order from mobility POS
    """,
    'author': 'ncliam',
    'depends': ['point_of_sale','base_import','account', 'product_expiry',
                    'purchase', 'sale', 'auth_signup','product_barcode_generator'],
    'data': [
             'security/security.xml',
             'security/ir.model.access.csv',
             'view/view.xml',
             'product_view.xml',
             'point_of_sale_view.xml',
             'master.xml',
             'operation.xml',
             'registration.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'qweb': [
        'static/src/xml/template.xml',
    ],   
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
