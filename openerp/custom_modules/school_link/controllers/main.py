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

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.osv import osv
from openerp.http import request
import datetime
from openerp.tools.translate import _
import phonenumbers

class SchoolLink_Controller(http.Controller):

    @http.route('/im_chat/post_delay', type="json", auth="public")
    def post_delay(self, uuid, message_type, message_content, delayTime):
        registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
        # execute the post method as SUPERUSER_ID
        message_id = registry["im_chat.message"].post_delay(cr, openerp.SUPERUSER_ID, uid, uuid, message_type,
                                                            message_content, delayTime, context=context)
        return message_id

    @http.route('/forgot_password_request', type='json', auth='none')
    def forgot_password_request(self, model, mobile):
        context = {}
        registry = request.registry
        cr = request.cr
        hr_employee = registry['hr.employee']
        res_partner = registry['res.partner']
        sms_authetication = registry['sms.authentication']

        user_id = None
        if model:
            if model == 'hr.employee':
                employee_ids = hr_employee.search(cr, SUPERUSER_ID, [('work_phone',"=", mobile)], context=context)
                employee_id = employee_ids and employee_ids[0] or None
                if employee_id:
                    user_id = hr_employee.browse(cr, SUPERUSER_ID, employee_id, context=context).user_id
                    user_id = user_id and user_id.id or None
            elif model == 'res.partner':
                partner_ids = res_partner.search(cr, SUPERUSER_ID, [('mobile', "=", mobile), ('customer', "=", False)], context=context)
                partner_id = partner_ids and partner_ids[0] or None
                if partner_id:
                    partner_id = res_partner.browse(cr, SUPERUSER_ID, partner_id, context=context)
                    user_id = partner_id.parent_user_id and partner_id.parent_user_id.id or None

        if not user_id:
            raise osv.except_osv(_('Error!'), _("There is no user with this mobile number"))

        token = sms_authetication.search(cr, SUPERUSER_ID, [('state', '=', 'sent'), ('mobile', '=', mobile)], limit=1)
        if token and token[0]:
            token = sms_authetication.browse(cr, SUPERUSER_ID, token[0])

        if not token:
            template = registry['ir.model.data'].get_object(cr, SUPERUSER_ID, 'school_link', 'registration_code_sms')

            verfication_code_data = {
                'mobile': mobile,
                'res_model': 'res.users',
                'res_id': user_id,
                'template_id': template.id,
            }
            token_id = sms_authetication.create(cr, SUPERUSER_ID, verfication_code_data, context=context)
            token = sms_authetication.browse(cr, SUPERUSER_ID, token_id, context=context)
            token.send_code()

        elif datetime.datetime.strptime(token.validity, "%Y-%m-%d %H:%M:%S") <= datetime.datetime.now():
            token.send_new_code()

        token_id = token.id
        return token_id

    @http.route('/forgot_password_verify', type='json', auth='none')
    def forgot_password_verify(self, token_id, typing_code, mobile, password):
        context = {}
        registry = request.registry
        cr = request.cr
        res_users = registry['res.users']
        sms_authetication = registry['sms.authentication']

        if not token_id and mobile:
            token_ids = sms_authetication.search(cr, SUPERUSER_ID, [('res_model','=','res.users'),('mobile', '=', mobile)], limit=1)
            token_id = token_ids and token_ids[0] or None

        if not token_id or not typing_code:
            raise osv.except_osv(_('error!'), _("Invalid Token"))

        token_ids = sms_authetication.search(cr, SUPERUSER_ID, [('id', '=', token_id)], limit=1)
        token = sms_authetication.browse(cr, SUPERUSER_ID, token_ids[0])
        mobile = token and token.mobile or mobile

        if not token.verify_code(typing_code):
            raise osv.except_osv(_('error!'), _("Wrong verification code"))

        user_id = res_users.browse(cr, SUPERUSER_ID, token.res_id, context=context)
        if user_id:
            res_users.write(cr, SUPERUSER_ID, user_id.id, {'password': password}, context=context)
            return True

        return False


    @http.route('/parent_registration', type='http', auth='none')
    def parent_registration(self, mobile, country_code=None):
        context = {}
        registry = request.registry
        cr = request.cr
        company_id = registry['res.users']._get_company(cr, SUPERUSER_ID, context=context)
        if not country_code:
            country_code = registry['res.company'].browse(cr, SUPERUSER_ID, company_id, context=context).country_id.code

        # Create partner with mobile number
        res_partner = registry['res.partner']
        sms_authetication = registry['sms.authentication']
        if mobile:
            formatted_mobile = phonenumbers.format_number(phonenumbers.parse(mobile, country_code), phonenumbers.PhoneNumberFormat.E164)
            partner_id = None
            existed = res_partner.search(cr, SUPERUSER_ID, [('mobile',"=", formatted_mobile),('customer',"=", False)], context=context)
            if not existed:

                partner_data = {
                    'name': mobile,
                    'mobile': mobile,
                    'email': mobile,
                    'company_id': company_id,
                    'customer': False,
                }
                partner_id = res_partner.create(cr, SUPERUSER_ID, partner_data, context=context)
            else:
                parner_id = existed and existed[0] or None

            token = sms_authetication.search(cr, SUPERUSER_ID, [('state', '=', 'sent'),('mobile','=', formatted_mobile)], limit=1)
            if token and token[0]:
                token = sms_authetication.browse(cr, SUPERUSER_ID, token[0])
                if datetime.datetime.strptime(token.validity, "%Y-%m-%d %H:%M:%S") <= datetime.datetime.now():
                    token = token.send_new_code()

            if not token:
                template = registry['ir.model.data'].get_object(cr, SUPERUSER_ID, 'school_link', 'registration_code_sms')

                verfication_code_data = {
                    'mobile': mobile,
                    'res_model': 'res.partner',
                    'res_id': partner_id,
                    'template_id': template.id,

                }
                token_id = sms_authetication.create(cr, SUPERUSER_ID, verfication_code_data, context=context)
                token = sms_authetication.browse(cr, SUPERUSER_ID, token_id, context=context)
                token.send_code()

            token_id = token.id
            cr.commit()
            return token_id

        raise osv.except_osv(_('error!'), _("Wrong use API"))


    @http.route('/parent_number_verify', type='json', auth='none')
    def parent_number_verify(self, token_id, typing_code, mobile, password, country_code=None):
        context = {}
        registry = request.registry
        cr = request.cr
        res_users = registry['res.users']
        res_partner = registry['res.partner']
        sms_authetication = registry['sms.authentication']
        company_id = res_users._get_company(cr, SUPERUSER_ID, context=context)
        if not country_code:
            country_code = registry['res.company'].browse(cr, SUPERUSER_ID, company_id, context=context).country_id.code

        if mobile:
            mobile = phonenumbers.format_number(phonenumbers.parse(mobile, country_code), phonenumbers.PhoneNumberFormat.E164)

        if not token_id and mobile:
            token_ids = sms_authetication.search(cr, SUPERUSER_ID, [('state', '=', 'sent'),('mobile', '=', mobile)], limit=1)
            token_id = token_ids and token_ids[0] or None

        if token_id and typing_code:
            token_ids = sms_authetication.search(cr, SUPERUSER_ID, [('id', '=', token_id)], limit=1)
            token = sms_authetication.browse(cr, SUPERUSER_ID, token_ids[0])
            mobile = token and token.mobile or mobile

            if not token.verify_code(typing_code):
                raise osv.except_osv(_('error!'), _("Wrong verification code"))

            user_id = res_users.search(cr, SUPERUSER_ID, [('partner_id.mobile','=', mobile)], context=context, limit=1)
            user_id = user_id and user_id[0] or None
            if not user_id:

                partner_id = res_partner.browse(cr, SUPERUSER_ID, token.res_id, context=context)

                group_ids = []
                dummy, group_id = registry["ir.model.data"].get_object_reference(cr, SUPERUSER_ID, 'school_link','group_school_parent')
                group_ids.append(group_id)

                user_data = {
                    'name': partner_id and partner_id.name or mobile,
                    'login': partner_id and partner_id.name or mobile,
                    'partner_id': partner_id and partner_id.id or None,
                    'password': password,
                    'company_id': company_id,
                    'company_ids': [(6, 0, [company_id])],
                    'group_id': [(6, 0, group_ids)],

                }
                user_id = res_users.create(cr, SUPERUSER_ID, user_data, context=context)

            return user_id

        raise osv.except_osv(_('error!'), _("Invalid Token"))


    @http.route('/parent_send_new_code', type='json', auth='none')
    def parent_send_new_code(self, token_id):
        registry = request.registry
        cr = request.cr
        token_ids = registry['sms.authentication'].search(cr, SUPERUSER_ID, [('id', '=', token_id)], limit=1)
        token = registry['sms.authentication'].browse(cr, SUPERUSER_ID, token_ids[0])
        if token:
            return token.send_new_code()

        raise osv.except_osv(_('error!'), _("Token is not found"))

