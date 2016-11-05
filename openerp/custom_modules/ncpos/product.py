# -*- coding: utf-8 -*-
#################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Julius Network Solutions SARL <contact@julius.fr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from openerp.osv import fields, orm, osv
from openerp.tools.translate import _

class product_template(osv.osv):
    _inherit = "product.template"

    def _default_category(self, cr, uid, context=None):
        res = super(product_template, self)._default_category(cr, uid, context=context)
        if not res:
            category_ids = self.pool.get().search(cr, uid, [('id', '>', 0)], context=context, limit=1)
            return category_ids and category_ids[0] or False
        return res


class product_category(orm.Model):
    _inherit = 'product.category'

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id
    
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', select=1),
    }

    _defaults = {
        'company_id': _get_default_company,
    }
    
