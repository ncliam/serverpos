# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import datetime
import random
import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp import api
from openerp.http import request
from openerp.osv import fields, osv
from openerp.tools.translate import _
import pytz

@api.model
def _lang_get(self):
    languages = self.env['res.lang'].search([])
    return [(language.code, language.name) for language in languages]

@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

# A good selection of easy to read password characters (e.g. no '0' vs 'O', etc.)
RANDOM_PASS_CHARACTERS = 'aaaabcdeeeefghjkmnpqrstuvwxyzAAAABCDEEEEFGHJKLMNPQRSTUVWXYZ23456789'
def generate_random_pass():
    return ''.join(random.SystemRandom().sample(RANDOM_PASS_CHARACTERS,10))

class POSRegistrationHome(http.Controller):

    @http.route('/web/pos_registration', type='json', auth='public')
    def pos_registration(self, business_name, email, phone):
        vals = {
            'name': business_name,
            'email': email,
            'phone': phone
        }
        return request.registry['pos.registration'].create(request.cr, SUPERUSER_ID, vals, context={})


class pos_registration(osv.osv):  
    _name = "pos.registration"
    
    _columns = {
        'name': fields.char('Business Name', required=True),
        'email': fields.char('Email', required=True),
        'phone': fields.char('Phone'),
        'password': fields.char('Password'),
        'currency_id': fields.many2one('res.currency', 'Currency'),
        'lang': fields.selection(_lang_get, 'Language'),
        'tz': fields.selection(_tz_get,  'Timezone', size=64),
        'state': fields.selection([('draft', 'Request'),
                                   ('approved', 'Approved')],
                                  'Status', readonly=True, copy=False),
        'company_id':fields.many2one('res.company', 'Company Created', readonly=True),
        'user_id': fields.many2one('res.users', 'User Created', readonly=True),
    }
    
    _defaults = {        
        'state': 'draft',
    }
    
    @api.cr_uid
    def send_daily_sales_email(self, cr, uid, ids=None, context=None):
        if context is None:
            context = {}
        if not ids:
            filters = [('state', '=', 'approved')]
            if 'filters' in context:
                filters.extend(context['filters'])
            ids = self.search(cr, uid, filters, context=context)
        mail_mail_obj = self.pool.get('mail.mail')
        pos_obj = self.pool.get('pos.order')
        current_date = datetime.date.today()
        for reg in self.browse(cr, uid, ids, context=context):
            if reg.state == 'approved':
                if reg.user_id and reg.user_id.partner_id and reg.user_id.partner_id.email:
                    email = reg.user_id.partner_id.email
                    # Send email to this account
                    today = current_date.strftime("%Y-%m-%d")
                    data = {
                        'form' : {
                        'date_start': today,
                        'date_end': today,
                        'user_ids': None, 
                        }                  
                    }
                    
                    pos_ids = pos_obj.search(cr, reg.user_id.id, [])
                    if pos_ids and len(pos_ids) > 0:
                        contentHTML = self.pool['report'].get_html(cr, uid, ids=pos_ids, report_name='point_of_sale.report_detailsofsales', data=data, context=context)                    
                        values = {
                            'model': None,
                            'res_id': None,
                            'subject': _('MedicPOS - Daily Sale Report'),
                            'body': None,
                            'body_html': contentHTML,
                            'parent_id': None,
                            'partner_ids': None,
                            'notified_partner_ids': None,
                            'attachment_ids': None,
                            'email_from': "admin@multimex.com.vn",
                            'email_to': email,
                        }
                        mail_id = mail_mail_obj.create(cr, uid, values, context=context)
                        mail_mail_obj.send(cr, uid, [mail_id], context=context)
                    
        # do somthing else
        return
    
    def action_aprrove(self, cr, uid, ids, context=None):
        
        for reg in self.browse(cr, uid, ids, context=context):
            
            # Create company
            company_id = reg.company_id and reg.company_id.id or False
            if not company_id:
                company_data = {
                    'name': reg.name,
                    'currency_id': reg.currency_id and reg.currency_id.id or False,                    
                }
                company_id = self.pool.get("res.company").create(cr, uid, company_data, context=context)
                self.write(cr, uid, reg.id, {'company_id': company_id}, context=context)
                
                #Config company accounting simple
                dummy,chart_template_id = self.pool.get("ir.model.data").get_object_reference(cr, SUPERUSER_ID, 'account', 'conf_chart0')
                date_start, date_stop, period = self.pool.get('account.config.settings')._get_default_fiscalyear_data(cr, uid, company_id, context=context)
                base_tax_domain = [("chart_template_id", "in", [chart_template_id]), ('parent_id', '=', False)]            
                sale_tax_domain = base_tax_domain + [('type_tax_use', 'in', ('sale','all'))]
                purchase_tax_domain = base_tax_domain + [('type_tax_use', 'in', ('purchase','all'))]
                sale_tax_id = self.pool.get('account.tax.template').search(cr, uid, sale_tax_domain, order="sequence, id desc")
                purchase_tax_id = self.pool.get('account.tax.template').search(cr, uid, purchase_tax_domain, order="sequence, id desc")
                
                account_config_id = self.pool.get('account.config.settings').create(cr, uid, {
                                                        'company_id': company_id,
                                                        'expects_chart_of_accounts': True,
                                                        'chart_template_id': chart_template_id,
                                                        'module_account_accountant': False,
                                                        'date_start': date_start,
                                                        'date_stop': date_stop,
                                                        'period': period,
                                                        'sale_tax': sale_tax_id and sale_tax_id[0] or False,
                                                        'purchase_tax': purchase_tax_id and purchase_tax_id[0] or False,
                                                    }, context=context)
                self.pool.get('account.config.settings').execute(cr, uid, [account_config_id], context=context)
                
            # Create user login
            user_id = reg.user_id and reg.user_id.id or False            
            if not user_id:
                group_ids = []
                dummy,group_id = self.pool.get("ir.model.data").get_object_reference(cr, SUPERUSER_ID, 'point_of_sale', 'group_pos_user')
                group_ids.append(group_id)
                dummy,group_id = self.pool.get("ir.model.data").get_object_reference(cr, SUPERUSER_ID, 'point_of_sale', 'group_pos_manager')
                group_ids.append(group_id)
                dummy,group_id = self.pool.get("ir.model.data").get_object_reference(cr, SUPERUSER_ID, 'ncpos', 'group_pos_admin')
                group_ids.append(group_id)
                user_data = {
                    'name': reg.email,
                    'login': reg.email,
                    'company_id': company_id,
                    'company_ids': [(6,0,[company_id])],
                    'group_id': [(6,0,group_ids)],
                    
                }
                user_id = self.pool.get("res.users").create(cr, uid, user_data, context=context)
                self.write(cr, uid, reg.id, {'user_id': user_id}, context=context)
                
            user = self.pool.get("res.users").browse(cr, uid, user_id, context=context)
            if user.partner_id:
                self.pool.get("res.partner").write(cr, uid, user.partner_id.id, {'email': reg.email, 'lang': reg.lang, 'tz': reg.tz }, context=context)
            
            #Create stock location            
            stock_location_id = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'internal'),('company_id', '=', company_id)], context=context)
            stock_location_id = stock_location_id and stock_location_id[0] or False
            if not stock_location_id:
                stock_data = {
                    'name': _('Stock Location of %s') % reg.name,
                    'usage': 'internal',
                    'company_id': company_id,
                }
                stock_location_id = self.pool.get('stock.location').create(cr, uid, stock_data, context=context)
                
            # Create Cash Payment method
            cash_journal_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'cash'),('company_id', '=', company_id)], context=context)
            cash_journal_id = cash_journal_id and cash_journal_id[0] or False
            if not cash_journal_id:
                cash_payment = {
                    'name': _('Cash'),
                    'type': 'cash',
                    'company_id': company_id,
                }
                cash_journal_id = self.pool.get('account.journal').create(cr, uid, cash_payment, context=context)
            
            # Create Bank Payment method
            bank_journal_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'bank'),('company_id', '=', company_id)], context=context)
            bank_journal_id = bank_journal_id and bank_journal_id[0] or False
            if not bank_journal_id:
                bank_payment = {
                    'name': _('Bank'),
                    'type': 'bank',
                    'company_id': company_id,
                }
                bank_journal_id = self.pool.get('account.journal').create(cr, uid, bank_payment, context=context)
                
            # Create Sale journal
            sale_journal_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale'),('company_id', '=', company_id)], context=context)
            sale_journal_id = sale_journal_id and sale_journal_id[0] or False
            if not sale_journal_id:
                sale_journal_data = {
                    'name': _('Sale Journal'),
                    'type': 'sale',
                    'company_id': company_id,
                }
                sale_journal_id = self.pool.get('account.journal').create(cr, uid, sale_journal_data, context=context)
            # Default Price list
            
            
             
            # Create POS Config
            pos_config_id = user.pos_config and user.pos_config.id or False
            if not user.pos_config:
                payment_ids = []
                payment_ids.append(cash_journal_id)
                payment_ids.append(bank_journal_id)                
                pricelist_id = self.pool.get('product.pricelist').create(cr, uid, {
                                                                            'name': _('Pricelist [%s]') % reg.name,
                                                                            'company_id': company_id,
                                                                            'type': 'sale',
                                                                            'currency_id': reg.currency_id and reg.currency_id.id or False,
                                                                        }, context=context)
                pos_config_data = {
                    'name': _('POS [%s]') % reg.name,
                    'journal_ids': [(6,0,payment_ids)],
                    'journal_id': sale_journal_id,
                    'stock_location_id': stock_location_id,
                    'company_id': company_id,
                    'pricelist_id': pricelist_id,
                }
                pos_config_id = self.pool.get('pos.config').create(cr, uid, pos_config_data, context=context)            
                self.pool.get("res.users").write(cr, uid, user_id, {'pos_config': pos_config_id}, context=context)
                
            # Create POS session
            session_id = self.pool.get('pos.session').search(cr, uid, [('state','=', 'opened'), ('user_id','=',user_id)], context=context)
            session_id = session_id and session_id[0] or False
            if not session_id:
                session_data = {
                    'user_id': user_id,
                    'config_id': pos_config_id
                }
                nosub_ctx = dict(context, mail_create_nosubscribe=True, mail_create_nolog=True)
                session_id = self.pool.get('pos.session').create(cr, user_id, session_data, context=nosub_ctx)
                pos_session = self.pool.get('pos.session').browse(cr, user_id, session_id, context=nosub_ctx)
                pos_session.signal_workflow('open')
                
            #Sent welcome email
            password = reg.password or generate_random_pass()
            self.pool.get("res.users").write(cr, uid, user_id, {'password': password}, context=context)
            self.write(cr, uid, reg.id, {'password':password}, context=context)
            #email_template = self.env.ref('ncpos.email_template_register_success', False)
            dummy,email_template = self.pool.get("ir.model.data").get_object_reference(cr, SUPERUSER_ID, 'ncpos', 'email_template_register_success')
            if email_template:
                context['lang'] = user.lang  # translate in targeted user language
                self.pool.get('email.template').send_mail(cr, uid, email_template, reg.id, force_send=True, raise_exception=False, context=context)
            
        return self.write(cr, uid, ids, {'state':'approved'}, context=context)
    
# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
