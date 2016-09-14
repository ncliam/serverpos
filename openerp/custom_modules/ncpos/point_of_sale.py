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
import datetime
import logging
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.osv import fields, osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
import base64
import openerp.addons.decimal_precision as dp
from openerp.addons.point_of_sale.report.pos_details import pos_details
_logger = logging.getLogger(__name__)

class pos_session(osv.osv):
    _inherit = 'pos.session'
    
    def wkf_action_open(self, cr, uid, ids, context=None):
        # second browse because we need to refetch the data from the DB for cash_register_id
        for record in self.browse(cr, uid, ids, context=context):
            values = {}
            if not record.start_at:
                values['start_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            values['state'] = 'opened'
            record.write(values)
            for st in record.statement_ids:
                st.button_open()

        return self.open_frontend_cb(cr, uid, ids, context=context)
    
    def open_frontend_cb(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if not ids:
            return {}
        
        force_by_admin = False
        for session in self.browse(cr, uid, ids, context=context):
            if session.user_id.id != uid:
                if (uid == SUPERUSER_ID):
                    force_by_admin = True
                    continue;
                raise osv.except_osv(
                        _('Error!'),
                        _("You cannot use the session of another users. This session is owned by %s. Please first close this one to use this point of sale." % session.user_id.name))
        context.update({'active_id': ids[0]})
        if force_by_admin:
            return;
        return {
            'type' : 'ir.actions.act_url',
            'target': 'self',
            'url':   '/pos/web/',
        }

class pos_order(osv.osv):
    _inherit = "pos.order"
    
    _columns = {
        'consumer_email': fields.char('Email of consumer', readonly=True, copy=False),
        'state': fields.selection([('draft', 'New'),
                                   ('failed', 'Failed'),
                                   ('cancel', 'Cancelled'),
                                   ('paid', 'Paid'),
                                   ('done', 'Posted'),
                                   ('invoiced', 'Invoiced')],
                                  'Status', readonly=True, copy=False),
    }

    def mark_failed(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, order.id, {'state': 'failed'}, context=context)

    # Temp fix for empty orders
    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}

        order_id = super(pos_order, self).create(cr, uid, values, context=context)
        order_row = self.browse(cr, uid, order_id, context=context)
        if order_row and order_row.lines and len(order_row) > 0:
            return order_id
        else:
            raise osv.except_osv(_('Error!'), _("POS order is empty"))

    
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
        order_id = self.create(cr, uid, self._order_fields(cr, uid, order, context=context), context)
        
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
        if context is None:
            context = {}
        context = {'create_from_mobility': True}
        order_ids = []
        for tmp_order in orders:
            
            to_invoice = tmp_order['to_invoice']
            order = tmp_order['data']

            # FIX failed
            if order['state'] == "failed":
                order['state'] = 'draft'
                if order["id"] > 0:
                    failed = self.browse(cr, uid, order["id"], context=context)
                    if failed:
                        self.unlink(failed.id)

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
    
    def pos_sales_details(self, cr, uid, form):
        details = pos_details(cr,uid,'Report',{})
        order_lines = details._pos_sales_details(form)
        payment_lines = details._get_payments(form)
        data = {
            'order_lines': order_lines,
             'payment_lines': payment_lines
        }
        return data
    
    

class pos_order_line(osv.osv):
    _inherit = "pos.order.line"
    
    _columns = {
        'name': fields.char('Line No', required=False, copy=False),
        'description': fields.char('Description', required=False, copy=False, state={'draft': [('readonly', False)]}, readonly=True),
        'uos': fields.many2one('product.uom', 'Product UoS', state={'draft': [('readonly', False)]}, readonly=True),        
        'uos_qty': fields.float('Quantity (UOS)', digits_compute=dp.get_precision('Product UoS')),
        'uos_price_unit': fields.float(string='Unit Price (UOS)', digits_compute=dp.get_precision('Product Price')),
    }

    
    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        if context.has_key('create_from_mobility'):
            uos_id = values['uos']
            uos = self.pool.get('product.uom').browse(cr, uid, uos_id, context=context)
            values['qty'] = values['uos_qty'] * uos.factor_inv
            values['price_unit'] = (values['uos_qty'] * values['uos_price_unit']) / values['qty']

        if not values.has_key("name") or values['name'] == None:
            values['name'] = "/"

        return super(pos_order_line, self).create(cr, uid, values, context=context)

    
    
class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'
    
    def onchange_life_date(self, cr, uid, ids, life_date=False, product_id=False, context=None):
        res = {}
        if not product_id:
            return res
        
        res['value'] = {
            #'life_date': _get_date_by_date('life_time', life_date),
            'use_date': self._get_date_by_date(cr, uid, 'use_time',product_id,  life_date, context=context),
            'removal_date': self._get_date_by_date(cr, uid, 'removal_time', product_id, life_date, context=context),
            'alert_date': self._get_date_by_date(cr, uid, 'alert_time', product_id, life_date, context=context),
        }
        
        return res
    
    def _get_date_by_date(self, cr, uid, dtype, product_id, import_date=False, context=None):
        """Return a function to compute the limit date for this type"""
        date_imported = datetime.datetime.today()
        if import_date:
            date_imported = datetime.datetime.strptime(import_date, DEFAULT_SERVER_DATETIME_FORMAT)
            
        """Compute the limit date for a given date"""
        if context is None:
            context = {}
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        duration = getattr(product, dtype)
        # set date to False when no expiry time specified on the product
        date = duration and date_imported + datetime.timedelta(days=duration)
        return date and date.strftime('%Y-%m-%d %H:%M:%S') or False
    
    @api.multi
    def name_get(self):
        
        result = []
        for lot in self:
            l_name = lot.ref and '[' + lot.ref + '] ' or ''
            l_name += lot.name            
            result.append((lot.id, l_name))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('ref', operator, name)] + args, limit=limit)
            
        return recs.name_get()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
