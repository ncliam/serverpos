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
    'name': 'School Link',
    'version': '1.0.0',
    'category': 'Education',
    'sequence': 6,
    'summary': 'Shool link helps parents and teacher new channel to discuss',
    'description': """

School Link
===========================

This module act as back-end of School Link solution. 

Main Features
-------------
* 
    """,
    'author': 'ncliam',
    'depends': ['hr', 'im_chat','auth_signup', 'website_sms_authentication_base_phone'],
    'data': [
             'security/security.xml',
             'security/ir.model.access.csv',
             'school_view.xml',
             'school_data.xml'
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'qweb': [],   
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
