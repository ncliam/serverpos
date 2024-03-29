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
    'name': 'Pricelist with UoM',
    'version': '1.0.1',
    'category': 'Sales Management',
    'sequence': 6,
    'summary': 'Support price base on UoM',
    'description': """

Pricelist with UoM
===========================

This module allows you config the pricelist base on product unit of messure . 

Main Features
-------------
* Add UoM into product.pricelist.item
    """,
    'author': 'ncliam',
    'depends': ['product'],
    'data': [
             'security/security.xml',
             'security/ir.model.access.csv',
             'pricelist_view.xml',],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'qweb': [],   
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
