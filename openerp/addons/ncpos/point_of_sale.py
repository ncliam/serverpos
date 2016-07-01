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

import time
from openerp.osv import fields, osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
import base64
import openerp.addons.decimal_precision as dp


class pos_order(osv.osv):
    _inherit = "pos.order"
    
    _columns = {
        'consumer_email': fields.char('Email of consumer', readonly=True, copy=False),
    }
    
    def _process_mobility_order(self, cr, uid, order, context=None):
                
        if 'name' not in order or order['name'] is False:
            order['name'] = "/"                
        if 'partner_id' not in order:
            order['partner_id'] = False
        if 'pos_session_id' not in order:
            session = super(pos_order, self)._default_session(cr, uid, context=context)
            if session is False:
                raise osv.except_osv( _('Error!'), _("POS order is not attached to an opened session."))
            order['pos_session_id'] = session
        
        session = self.pool.get('pos.session').browse(cr, uid, order['pos_session_id'], context=context)  
        # Create new order
        order_id = self.create(cr, uid, self._order_fields(cr, uid, order, context=context),context)        
        
        for payments in order['statement_ids']:
            if ('statement_id' not in payments[2]):
                payments[2]['statement_id'] = False
            self.add_payment(cr, uid, order_id, self._payment_fields(cr, uid, payments[2], context=context), context=context)
            
        # Get order created
        order_row = self.browse(cr, uid, order_id, context=context)
        order['amount_return'] = abs(order_row['amount_total'] - order_row['amount_paid'])
        
        if not float_is_zero(order['amount_return'], self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')):
            cash_journal = session.cash_journal_id
            if not cash_journal:
                cash_journal_ids = filter(lambda st: st.journal_id.type=='cash', session.statement_ids)
                if not len(cash_journal_ids):
                    raise osv.except_osv( _('error!'),
                        _("No cash statement found for this session. Unable to record returned cash."))
                cash_journal = cash_journal_ids[0].journal_id
            self.add_payment(cr, uid, order_id, {
                'amount': -order['amount_return'],
                'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_name': _('return'),
                'journal': cash_journal.id,
            }, context=context)
        return order_id

    def create_from_mobility(self, cr, uid, orders, context=None):
        order_ids = []
        for tmp_order in orders:
            
            to_invoice = tmp_order['to_invoice']
            order = tmp_order['data']
            order_id = self._process_mobility_order(cr, uid, order, context=context)
            order_ids.append(order_id)

            try:
                self.signal_workflow(cr, uid, [order_id], 'paid')
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

            if to_invoice:
                self.action_invoice(cr, uid, [order_id], context)
                order_obj = self.browse(cr, uid, order_id, context)
                self.pool['account.invoice'].signal_workflow(cr, uid, [order_obj.invoice_id.id], 'invoice_open')

        return order_ids
    
    def report_sale_details(self, cr, uid, ids, report_name, html=None, data=None, context=None):
        content = self.pool['report'].get_pdf(cr, uid, ids, report_name, html=html, data=data, context=context)
        return base64.encodestring(content)

class pos_order_line(osv.osv):
    _inherit = "pos.order.line"
    
    _columns = {        
        'description': fields.char('Description', required=False, copy=False, state={'draft': [('readonly', False)]}, readonly=True),
        'uos_qty': fields.float('Quantity (UoS)' ,digits_compute= dp.get_precision('Product UoS'), state={'draft': [('readonly', False)]}, readonly=True),
        'uos': fields.many2one('product.uom', 'Product UoS', state={'draft': [('readonly', False)]}, readonly=True),
    }
    
    def create(self, cr, uid, values, context=None):
        if (not values.has_key("qty")):
            values.update({
                'qty': values.get('uos_qty'),
            })
        newId = super(pos_order_line, self).create(cr, uid, values, context=context)
        line = self.browse(cr, uid, newId, context=context)
        qty = self.pool.get('product.uom')._compute_qty(cr, uid, line.uos.id, line.uos_qty, line.product_id.uom_id.id)
        self.write(cr, uid, [newId], {'qty': qty})
        return newId


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
