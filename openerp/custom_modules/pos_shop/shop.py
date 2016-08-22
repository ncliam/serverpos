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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class pos_shop(osv.osv):
    _name = 'pos.shop'
    
    _columns = {
        'name': fields.char('Shop Name', required=True),
        'company_id':fields.many2one('res.company', 'Company', required=True),
        'currency_id':fields.many2one('res.currency', 'Currency'),
        'config_ids': fields.one2many('pos.config', 'shop_id', 'POS Devices', readonly=True),
        'stock_location_id': fields.many2one('stock.location', 'Stock Location', domain=[('usage', '=', 'internal')]),
        'pricelist_id': fields.many2one('product.pricelist','Pricelist'),
        'journal_id' : fields.many2one('account.journal', 'Sale Journal', domain=[('type', '=', 'sale')]),
        'address': fields.char('Address'),        
        'hotline': fields.char('Hotline'),        
        'email': fields.char('Email'),
    }
    
    def _default_sale_journal(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        res = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale'), ('company_id', '=', company_id)], limit=1, context=context)
        return res and res[0] or False

    def _default_pricelist(self, cr, uid, context=None):
        res = self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')], limit=1, context=context)
        return res and res[0] or False

    def _get_default_location(self, cr, uid, context=None):
        wh_obj = self.pool.get('stock.warehouse')
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        res = wh_obj.search(cr, uid, [('company_id', '=', user.company_id.id)], limit=1, context=context)
        if res and res[0]:
            return wh_obj.browse(cr, uid, res[0], context=context).lot_stock_id.id
        return False

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        return company_id
    
    _defaults = {      
        'journal_id': _default_sale_journal,  
        'stock_location_id': _get_default_location,
        'company_id': _get_default_company,
        'pricelist_id': _default_pricelist,
    }
    
class pos_config(osv.osv):
    _inherit = 'pos.config'
    
    _columns = {
        'shop_id':fields.many2one('pos.shop', 'Shop', required=True),
        'udi': fields.char('Unique Device Indentifier', help="Restrict this Point of Sale to a physical device"),
    }

    
