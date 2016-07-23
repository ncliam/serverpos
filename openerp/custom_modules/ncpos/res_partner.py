# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _


class res_partner(osv.osv):
    
    _inherit = "res.partner"
    _columns = {
        'billing_email_template': fields.many2one('email.template', 'Billing email template', help="Template document of billing email"), 
    }

class res_user(osv.osv):
    _inherit = "res.users"   
    
    def _get_group(self,cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        result = []
        try:
            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'base', 'group_user')
            result.append(group_id)
            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'point_of_sale', 'group_pos_user')
            result.append(group_id)            
        except ValueError:
            # If these groups does not exists anymore
            pass
        return result
    
    def get_application_groups(self, cr, uid, domain=None, context=None):  
        """ return the list of groups available to an user to generate virtual fields """  
        got_share = self.pool['ir.model.fields'].search_count(cr, uid, [('name', '=', 'share'), ('model', '=', 'res.groups')], context=context)  
        if got_share:  
            if domain is None:  
                domain = []  
            # remove non-shared groups in SQL as 'share' may not be in _fields  
            cr.execute("SELECT id FROM res_groups WHERE share IS true")  
            domain.append(('id', 'not in', [gid for (gid,) in cr.fetchall()]))  
        return self.search(cr, uid, domain or [])  
    
    _defaults = {        
        'groups_id': _get_group,
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
