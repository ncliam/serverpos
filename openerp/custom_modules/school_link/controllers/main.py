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

from openerp import SUPERUSER_ID
from openerp import http
from openerp.osv import osv
from openerp.http import request
import datetime
from openerp.tools.translate import _

class SMSRegistrationHome(http.Controller):

    @http.route('/parent_registration', type='json', auth='public')
    def parent_registration(self, mobile):
        context = {}

        company_id = request.registry['res.users']._get_company(request.cr, SUPERUSER_ID, context=context)

        # Create partner with mobile number
        res_partner = request.registry['res.partner']
        sms_authetication = request.registry['sms.authentication']
        if mobile:

            partner_id = None
            existed = res_partner.search_count(request.cr, SUPERUSER_ID, [('mobile',"=", mobile),('customer',"=", True)], context=context)
            if not existed:

                partner_data = {
                    'name': _('Mobile user Mapping'),
                    'mobile': mobile,
                    'company_id': company_id,
                    'customer': True,
                }
                partner_id = res_partner.create(request.cr, SUPERUSER_ID, partner_data, context=context)

            token = sms_authetication.search(request.cr, SUPERUSER_ID, [('state', '=', 'sent'),('mobile','=', mobile)], limit=1)
            if token and token[0]:
                token = sms_authetication.browse(request.cr, SUPERUSER_ID, token[0])

            if not token:
                template = request.registry['ir.model.data'].get_object(request.cr, SUPERUSER_ID, 'school_link', 'registration_code_sms')

                verfication_code_data = {
                    'mobile': mobile,
                    'res_model': 'res.partner',
                    'res_id': partner_id,
                    'template_id': template.id,

                }
                token_id = sms_authetication.create(request.cr, SUPERUSER_ID, verfication_code_data, context=context)
                token = sms_authetication.browse(request.cr, SUPERUSER_ID, token_id, context=context)
                token.send_code()

            elif datetime.datetime.strptime(token.validity,"%Y-%m-%d %H:%M:%S") <= datetime.datetime.now():
                token.send_new_code()

            token_id = token.id
            return token_id



        raise osv.except_osv(_('error!'), _("Wrong use API"))


    @http.route('/parent_number_verify', type='json', auth='public')
    def parent_number_verify(self, token_id, typing_code, mobile, password):
        context = {}
        res_users = request.registry['res.users']
        res_partner = request.registry['res.partner']
        sms_authetication = request.registry['sms.authentication']
        company_id = res_users._get_company(request.cr, SUPERUSER_ID, context=context)

        if not token_id and mobile:
            token_ids = sms_authetication.search(request.cr, SUPERUSER_ID, [('mobile', '=', mobile)], limit=1)
            token_id = token_ids and token_ids[0] or None

        if token_id and typing_code:
            token_ids = sms_authetication.search(request.cr, SUPERUSER_ID, [('id', '=', token_id)], limit=1)
            token = sms_authetication.browse(request.cr, SUPERUSER_ID, token_ids[0])
            mobile = token and token.mobile or mobile

            if not token.verify_code(typing_code):
                raise osv.except_osv(_('error!'), _("Wrong verification code"))

            user_id = res_users.search(request.cr, SUPERUSER_ID, [('partner_id.mobile','=', mobile)], context=context, limit=1)
            user_id = user_id and user_id[0] or None
            if not user_id:

                partner_id = res_partner.browse(request.cr, SUPERUSER_ID, token.res_id, context=context)

                group_ids = []
                dummy, group_id = request.registry["ir.model.data"].get_object_reference(request.cr, SUPERUSER_ID, 'school_link','group_school_parent')
                group_ids.append(group_id)

                user_data = {
                    'name': partner_id and partner_id.mobile or mobile,
                    'login': partner_id and partner_id.mobile or mobile,
                    'partner_id': partner_id and partner_id.id or None,
                    'password': password,
                    'company_id': company_id,
                    'company_ids': [(6, 0, [company_id])],
                    'group_id': [(6, 0, [group_ids])],

                }
                user_id = res_users.create(request.cr, SUPERUSER_ID, user_data, context=context)

            return user_id

        raise osv.except_osv(_('error!'), _("Wrong use API"))


    @http.route('/parent_send_new_code', type='json', auth='public')
    def parent_send_new_code(self, token_id):
        token_ids = request.registry['sms.authentication'].search(request.cr, SUPERUSER_ID, [('id', '=', token_id)], limit=1)
        token = request.registry['sms.authentication'].browse(request.cr, SUPERUSER_ID, token_ids[0])
        if token:
            return token.send_new_code()

            raise osv.except_osv(_('error!'), _("Token is not found"))

