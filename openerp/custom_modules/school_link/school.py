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

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
import datetime

from ast import literal_eval

class im_chat_session(osv.osv):
    _inherit = 'im_chat.session'

    def add_user(self, cr, uid, uuid, user_id, context=None):
        """ add the given user to the given session """
        sids = self.search(cr, uid, [('uuid', '=', uuid)], context=context, limit=1)
        for session in self.browse(cr, uid, sids, context=context):
            if user_id not in [u.id for u in session.user_ids]:
                self.write(cr, uid, [session.id], {'user_ids': [(4, user_id)]}, context=context)
                # notify the all the channel users and anonymous channel
                notifications = []
                for channel_user_id in session.user_ids:
                    info = self.session_info(cr, channel_user_id.id, [session.id], context=context)
                    notifications.append([(cr.dbname, 'im_chat.session', channel_user_id.id), info])
                # Anonymous are not notified when a new user is added : cannot exec session_info as uid = None
                info = self.session_info(cr, SUPERUSER_ID, [session.id], context=context)
                notifications.append([session.uuid, info])
                self.pool['bus.bus'].sendmany(cr, uid, notifications)
                # send a message to the conversation
                user = self.pool['res.users'].browse(cr, uid, user_id, context=context)
                chat_names = self.pool['res.users'].get_chat_name(cr, uid, [user.id], context=context)
                notify_msg = _('%s joined the conversation.') % (chat_names[user.id] or user.name)
                self.pool["im_chat.message"].post(cr, uid, uid, session.uuid, "meta", notify_msg, context=context)

    def users_infos(self, cr, uid, ids, context=None):
        """ get the user infos for all the user in the session """
        for session in self.pool["im_chat.session"].browse(cr, SUPERUSER_ID, ids, context=context):
            users_infos = self.pool["res.users"].read(cr, SUPERUSER_ID, [u.id for u in session.user_ids], ['id','name', 'im_status'], context=context)
            return users_infos

class sms_authentication(osv.osv):
    _name = 'sms.authentication'
    _inherit = ['sms.authentication', 'phone.common']
    _phone_fields = ['mobile']
    _phone_name_sequence = 10
    _country_field = None
    _partner_field = None

    def create(self, cr, uid, vals, context=None):
        vals_reformated = self._generic_reformat_phonenumbers(
            cr, uid, None, vals, context=context)
        return super(sms_authentication, self).create(
            cr, uid, vals_reformated, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals_reformated = self._generic_reformat_phonenumbers(
            cr, uid, ids, vals, context=context)
        return super(sms_authentication, self).write(
            cr, uid, ids, vals_reformated, context=context)

class email_template(osv.osv):
    _inherit = "email.template"

    def _get_default_gateway(self, cr, uid, context=None):
        gateway_id = self.pool.get('sms.smsclient').search(cr, uid, [], context=context, limit=1)
        return gateway_id and gateway_id[0] or None

    _defaults = {
        'sms_template': True,
        'gateway_id': _get_default_gateway,
    }


class res_user(osv.osv):
    _inherit = 'res.users'

    def _get_schools(self, cr, uid, context=None):

        school_ids = []
        res_user = self.pool.get('res.users')
        res_partner = self.pool.get('res.partner')

        user_id = res_user.browse(cr, SUPERUSER_ID, uid, context=context)
        if user_id.partner_id and user_id.partner_id.mobile:
            mobile = user_id.partner_id.mobile
            partner_ids = res_partner.search(cr, SUPERUSER_ID, [('mobile', '=', mobile), ('customer', '=', True)],
                                             context=context)
            if (partner_ids):
                for partner_id in partner_ids:
                    partner = res_partner.browse(cr, SUPERUSER_ID, partner_id, context=context)
                    if partner and partner.company_id and partner.company_id.school:
                        school_ids.append(partner.company_id.id)

        return school_ids


    def _get_all_children(self, cr, uid, context=None):

        child_ids = []
        res_user = self.pool.get('res.users')
        res_partner = self.pool.get('res.partner')

        user_id = res_user.browse(cr, SUPERUSER_ID, uid, context=context)
        if user_id.partner_id and user_id.partner_id.mobile:
            mobile = user_id.partner_id.mobile
            partner_ids = res_partner.search(cr, SUPERUSER_ID, [('mobile', '=', mobile), ('customer', '=', True)],
                                             context=context)
            if (partner_ids):
                for partner_id in partner_ids:
                    partner = res_partner.browse(cr, SUPERUSER_ID, partner_id, context=context)
                    for child_id in partner.children:
                        child_ids.append(child_id.id)

        return child_ids


    def get_relate_schools(self, cr, uid, ids, name, args, context=None):
        res = {}
        for user_id in self.browse(cr, SUPERUSER_ID, ids, context=context):
            res[user_id.id] = self._get_schools(cr, user_id.id, context=context)
        return res

    def get_all_children(self, cr, uid, ids, name, args, context=None):
        res = {}
        for user_id in self.browse(cr, SUPERUSER_ID, ids, context=context):
            res[user_id.id] = self._get_all_children(cr, user_id.id, context=context)
        return res

    def select_school(self, cr, uid, school=None, context=None):
        if school:
            company_id = self.pool.get('res.company').browse(cr, SUPERUSER_ID, school, context=context)
            if company_id:
                user_data = {
                    'company_id': company_id.id,
                    'company_ids': [(6, 0, [company_id.id])],
                }
                self.pool.get("res.users").write(cr, SUPERUSER_ID, uid, user_data, context=context)

        else:
            raise osv.except_osv(_('error!'), _("Invalid school selected"))


    def get_chat_name(self, cr, uid, user_ids, context=None):
        result = {}
        for user_id in user_ids:
            user = self.browse(cr, SUPERUSER_ID, user_id, context=context)
            company_id = user.company_id.id
            name = user.name

            employee_ids = self.pool.get('hr.employee').search(cr, SUPERUSER_ID, [("user_id",'=', user_id)], context=context)
            employee_id = employee_ids and employee_ids[0] or None

            if not employee_id:
                mobile = user.partner_id.mobile
                if mobile:
                    # search parent in school
                    parent_ids = self.pool.get('res.partner').search(cr, SUPERUSER_ID, [("mobile", '=', mobile),
                                                                                        ('customer','=', True),
                                                                                        ('company_id','=', company_id)], context=context)
                    if not parent_ids or len(parent_ids) == 0:
                        # search parent not in school
                        parent_ids = self.pool.get('res.partner').search(cr, SUPERUSER_ID, [("mobile", '=', mobile),
                                                                                            ('customer', '=', True)], context=context)
                    parent_id = parent_ids and parent_ids[0] or None
                    if parent_id:
                        parent = self.pool.get('res.partner').browse(cr, SUPERUSER_ID, parent_id, context=context)
                        name = parent.name
            else:
                employee = self.pool.get('hr.employee').browse(cr, SUPERUSER_ID, employee_id, context=context)
                name = employee.name

            result[user_id] = name

        return result

    _columns = {
        'school_ids': fields.function(get_relate_schools, relation='res.company', type='many2many',
                                           string='Related Schools', readonly=True),
        'children': fields.function(get_all_children, relation='hr.employee', type='many2many',
                                           string='Children', readonly=True),
    }

    def signup(self, cr, uid, values, token=None, context=None):
        if context is None:
            context = {}

        code_obj = self.pool.get('sms.authentication')
        if context.has_key('verify_phonenumber'):
            if token:
                if not values.has_key("written_code"):
                    raise osv.except_osv(_('error!'), _("No verification code"))
                written_code =  values['written_code']

                code_ids = code_obj.search(cr, uid, [('id', '=', token)], limit=1)
                code = code_obj.browse(cr, uid, code_ids[0])
                if not code or code.state == 'cancel' or datetime.datetime.strptime(code.validity, "%Y-%m-%d %H:%M:%S") <= datetime.datetime.now() :
                    raise osv.except_osv(_('error!'), _("Invalid verification code (Expired or Cancelled)."))

                if not code_obj.verify_code(written_code):
                    raise osv.except_osv(_('error!'), _("Wrong verification code"))

                return self._create_parent_user(cr, uid, values, context=context)

            else:
                verfication_code_data = {
                    'mobile': values['login'],
                    'country_id': 243,

                }
                code_id = code_obj.create(cr, uid, verfication_code_data, context=context)
                return code_id

        else:
            return super(res_user, self).signup(cr, uid, values, token=False, context=context)


    def _create_parent_user(self, cr, uid, values, context=None):
        """ create a new user from the template user """
        ir_config_parameter = self.pool.get('ir.config_parameter')
        template_user_id = literal_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.template_user_id', 'False'))
        assert template_user_id and self.exists(cr, uid, template_user_id, context=context), 'Signup: invalid template user'

        assert values.get('login'), "Signup: no login given for new user"
        assert values.get('partner_id') or values.get('name'), "Signup: no name or partner given for new user"

        # create a copy of the template user (attached to a specific partner_id if given)
        values['active'] = True
        context = dict(context or {}, no_reset_password=True)
        return self.copy(cr, uid, template_user_id, values, context=context)


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def get_parent_user(self, cr, uid, ids, name, args, context=None):
        res = {}
        for partner_id in self.browse(cr, SUPERUSER_ID, ids, context=context):
            mobile = partner_id.mobile
            if mobile:
                same_mobile_ids = self.search(cr, SUPERUSER_ID, [('mobile','=',mobile)], context=context)
                related_users = self.pool.get('res.users').search(cr, SUPERUSER_ID, [('partner_id','in', same_mobile_ids)], context=context)
                res[partner_id.id] = related_users and related_users[0] or None
            else:
                res[partner_id.id] = None
        return res

    _columns = {
        'children': fields.many2many('hr.employee', 'parent_student_rel', 'student_id', 'partner_id', 'Childs', readonly=True),
        'parent_user_id': fields.function(get_parent_user, relation='res.users', type='many2one', string='Related User', readonly=True),

        'property_account_payable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Payable",
            domain="[('type', '=', 'payable')]",
            help="This account will be used instead of the default one as the payable account for the current partner",
            required=False),
        'property_account_receivable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as the receivable account for the current partner",
            required=False),
    }

    def create_multi(self, cr, uid, datas, context=None):
        if context is None:
            context = {}
        partner_ids = []
        for vals in datas:
            partner_id = self.create(cr, uid, vals, context=context)
            partner_ids.append(partner_id)

        return partner_ids


class res_company(osv.osv):
    _inherit = 'res.company'

    def get_study_child(self, cr, uid, ids, name, args, context=None):
        res = {}
        for school_id in self.browse(cr, uid, ids, context=context):
            res[school_id.id] = self._get_children(cr, uid, school_id.id, context=context)
        return res

    def _get_children(self, cr, uid, school, context=None):
        childs = []

        user_id = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user_id.partner_id and user_id.partner_id.mobile:
            mobile = user_id.partner_id.mobile
            partner_ids = self.pool.get('res.partner').search(cr, SUPERUSER_ID, [('mobile', '=', mobile), ('customer', '=', True),('company_id', '=', school)], context=context)
            if (partner_ids):
                partner_ids = self.pool.get('res.partner').browse(cr, SUPERUSER_ID, partner_ids, context=context)
                for partner_id in partner_ids:
                    if partner_id.children:
                        for x in partner_id.children:
                            childs.append(x.id)

        return childs

    def name_get(self, cr, uid, ids, context=None):
        return super(res_company, self).name_get(cr, SUPERUSER_ID, ids, context=context)

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'display_name': fields.function(_name_get_fnc, type="char", string='Display Name', store=True),
        'school': fields.boolean('School'),
        'children': fields.function(get_study_child, relation='hr.employee', type='many2many', string='Childs in study', readonly=True),
    }


class hr_employee(osv.osv):
    _name = "hr.employee"
    _inherit = ['hr.employee', 'phone.common']
    _phone_fields = ['work_phone', 'mobile_phone']
    _phone_name_sequence = 10
    _country_field = None
    _partner_field = None

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id

    def create(self, cr, uid, vals, context=None):
        vals_reformated = self._generic_reformat_phonenumbers(
            cr, uid, None, vals, context=context)
        return super(hr_employee, self).create(
            cr, uid, vals_reformated, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals_reformated = self._generic_reformat_phonenumbers(
            cr, uid, ids, vals, context=context)
        return super(hr_employee, self).write(
            cr, uid, ids, vals_reformated, context=context)

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for emp in self.browse(cr, SUPERUSER_ID, ids, context=context):
            name = emp.name
            last = emp.last_name
            if last:
                name = last + " " + name
            res.append((emp.id, name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    def get_teach_subjects(self, cr, uid, ids, name, args, context=None):
        res = {}
        for emp in self.browse(cr, uid, ids, context=context):
            subjects = []
            schedule_line_ids = self.pool.get('school.schedule.line').search(cr, uid, [('teacher_id','=', emp.id),('class_id.active','=',True)], context=context)
            if schedule_line_ids:
                for schedule_line in self.pool.get('school.schedule.line').browse(cr, uid, schedule_line_ids, context=context):
                    if schedule_line.subject_id:
                        subjects.append(schedule_line.subject_id.id)

            subjects = self.pool.get('school.subject').search(cr, uid, [('id','in', subjects)], context=context)
            res[emp.id] = subjects
        return res


    def get_teach_classes(self, cr, uid, ids, name, args, context=None):
        res = {}
        for emp in self.browse(cr, uid, ids, context=context):
            classes = []
            schedule_line_ids = self.pool.get('school.schedule.line').search(cr, uid, [('teacher_id', '=', emp.id),
                                                                                       ('class_id.active', '=', True)],
                                                                             context=context)
            if schedule_line_ids:
                for schedule_line in self.pool.get('school.schedule.line').browse(cr, uid, schedule_line_ids, context=context):
                        classes.append(schedule_line.class_id.id)

            classes = self.pool.get('school.class').search(cr, uid, [('id','in', classes)], context=context)
            res[emp.id] = classes
        return res


    _columns = {
        'last_name': fields.char('Last Name'),
        'display_name': fields.function(_name_get_fnc, type="char", string='Display Name', store=True),
        'home_town': fields.char('Home town'),
        'home_address': fields.char('Home Address'),
        'teacher': fields.boolean('Is a Teacher'),
        'student': fields.boolean('Is a Student'),
        'parent_ids': fields.many2many('res.partner', 'parent_student_rel', 'partner_id', 'student_id', 'Parents'),
        'class_ids': fields.many2many('school.class', 'school_class_student_rel', 'student_id', 'class_id', 'Classes', domain="[('active','=',True)]"),
        'subject_ids': fields.function(get_teach_subjects, relation='school.subject', type='many2many', string='Teaching Subjects', readonly=True),
        'teaching_class_ids': fields.function(get_teach_classes, relation='school.class', type='many2many', string='Teaching Classes', readonly=True),

    }

    _defaults = {
        'company_id': _get_default_company,
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        context = dict(context, mail_create_nosubscribe=True)
        return super(hr_employee, self).create(cr, uid, values, context=context)

    def create_multi(self, cr, uid, datas, context=None):
        if context is None:
            context = {}
        emp_ids = []
        for vals in datas:
            emp_id = self.create(cr, uid, vals, context=context)
            emp_ids.append(emp_id)

        return emp_ids

class school_scholarity(osv.osv):
    _name = 'school.scholarity'

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id

    def _search_active(self, cr, uid, obj, name, args, context):
        res = []
        for field, operator, value in args:
            where = ""
            assert value in (True, False), 'Operation not supported'
            now = datetime.datetime.now().strftime(DATETIME_FORMAT)
            if (operator == '=' and value == True) or (operator == '!=' and value == False):
                where = " WHERE date_start <= '%s' AND date_end >= '%s'" % (now, now)
            else:
                where = " WHERE date_start > '%s' OR date_end < '%s'" % (now, now)

            cr.execute('select id FROM school_scholarity %s' % (where,))
            res_ids = [x[0] for x in cr.fetchall()]
            res.append(('id', "in", res_ids))
        return res


    def _is_active(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        now = datetime.datetime.now()
        for scholarity in self.browse(cr, uid, ids, context=context):
            res[scholarity.id] = True
            if scholarity.date_start:
                ds = datetime.datetime.strptime(scholarity.date_start, '%Y-%m-%d %H:%M:%S')
                if ds > now:
                    res[scholarity.id] = False

            if scholarity.date_end:
                de = datetime.datetime.strptime(scholarity.date_end, '%Y-%m-%d %H:%M:%S')
                if de < now:
                    res[scholarity.id] = False


        return res

    _columns = {
        'name': fields.char('Scholarity Year', required=True),
        'company_id':fields.many2one('res.company', 'School', domain="[('school','=',True)]"),
        'date_start': fields.datetime('Start Date', required=True),
        'date_end': fields.datetime('End Date', required=True),
        'active': fields.function(_is_active, store=False, string='Active', type='boolean', fnct_search=_search_active),
    }

    _defaults = {
        'company_id': _get_default_company,
    }
    
class school_class_group(osv.osv):
    _name = 'school.class.group'

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id
    
    _columns = {
        'name': fields.char('Name', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list "),  
    }

    _defaults = {
        'company_id': _get_default_company,
    }

    def _check_duplicate(self, cr, uid, ids, context=None):
        for group in self.browse(cr, uid, ids, context=None):
            domain = [
                ('name', '=', group.name),
                ('company_id','=', group.company_id.id)
            ]
            count = self.search_count(cr, uid, domain, context=context)
            if count > 1:
                return False
        return True

    _constraints = [
        (_check_duplicate, 'Duplicate group name',['name']),
    ]
    
class school_subject(osv.osv):
    _name = 'school.subject'

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id
    
    _columns = {
        'name': fields.char('Name', required=True),
        'company_id':fields.many2one('res.company', 'School', domain="[('school','=',True)]"),
        'weight': fields.integer('Weight', help="Define weight to calculate average"),  
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list "),  
    }

    _defaults = {
        'company_id': _get_default_company,
    }

    def _check_duplicate(self, cr, uid, ids, context=None):
        for subject in self.browse(cr, uid, ids, context=None):
            domain = [
                ('name', '=', subject.name),
                ('company_id','=', subject.company_id and subject.company_id.id or False)
            ]
            count = self.search_count(cr, uid, domain, context=context)
            if count > 1:
                return False
        return True

    _constraints = [
        (_check_duplicate, 'Duplicate subject name',['name']),
    ]


class school_class(osv.osv):
    _name = 'school.class'

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id

    def _get_all_teachers(self, cr, uid, ids, name, args, context=None):
        res = {}
        for class_id in self.browse(cr, uid, ids, context=context):
            teacher_ids = []
            teacher_ids.append(class_id.teacher_id.id) # add primary teacher

            schedule_line_ids = self.pool.get('school.schedule.line').search(cr, uid,[('schedule_id.class_id', '=', class_id.id)], context=context)
            schedule_lines = self.pool.get('school.schedule.line').browse(cr, uid, schedule_line_ids, context=context)
            for schedule_line in schedule_lines:
                teacher_ids.append(schedule_line.teacher_id.id) # add other teachers

            all_teacher_ids = self.pool.get('hr.employee').search(cr, uid, [('id', 'in', teacher_ids)], context=context)
            res[class_id.id] = all_teacher_ids

        return res

    def _get_all_parents(self, cr, uid, ids, name, args, context=None):
        res = {}
        for class_id in self.browse(cr, uid, ids, context=context):
            parent_ids = []
            for student in class_id.student_ids:
                student_parent_ids = student.parent_ids
                for parent_id in student_parent_ids:
                    parent_ids.append(parent_id.id)

            all_parent_ids = self.pool.get('res.partner').search(cr, uid, [('id', 'in', parent_ids)], context=context)
            res[class_id.id] = all_parent_ids

        return res

    def _check_duplicate(self, cr, uid, ids, context=None):
        for school_class in self.browse(cr, uid, ids, context=None):
            domain = [
                ('name', '=', school_class.name),
                ('year_id', '=', school_class.year_id.id)
                ('company_id','=', school_class.company_id.id)
            ]
            count = self.search_count(cr, uid, domain, context=context)
            if count > 1:
                return False
        return True

    _columns = {
        'name': fields.char('Name', required=True),
        'year_id':fields.many2one('school.scholarity', 'Year', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'group_id':fields.many2one('school.class.group', 'Group', required=True, ondelete="cascade"),
        'teacher_id':fields.many2one('hr.employee', 'Responsible', domain="[('teacher','=',True)]", ondelete="cascade"),
        'student_ids':fields.many2many('hr.employee', 'school_class_student_rel', 'class_id', 'student_id', 'Students', domain="[('student','=',True)]"),
        'active': fields.related('year_id', 'active', type='boolean', string='Active'),
        'teacher_ids': fields.function(_get_all_teachers, relation='hr.employee', type='many2many', string='Teachers',readonly=True),
        'parent_ids': fields.function(_get_all_parents, relation='res.partner', type='many2many', string='Parents', readonly=True),
    }

    _constraints = [
        (_check_duplicate, 'Duplicate class name', ['name']),
    ]

    _defaults = {
        'company_id': _get_default_company,
    }
    

class school_exam_move(osv.osv):
    _name = 'school.exam.move'

    def _get_default_teacher(self, cr, uid, context=None):
        teacher_ids = self.pool.get('hr.employee').search(cr, uid, [('teacher', '=', True), ('user_id', "=", uid)],context=context)
        return teacher_ids and teacher_ids[0] or None

    _columns = {
        'name': fields.char('Name'),
        'class_id': fields.many2one('school.class', 'Class', required=True, ondelete="cascade"),
        'teacher_id': fields.many2one('hr.employee', 'Teacher', required=True, domain=[('teacher', '=', True)], ondelete="cascade"),
        'student_id': fields.many2one('hr.employee', 'Student', required=True, domain=[('student', '=', True)], ondelete="cascade"),
        'mark': fields.float('Mark'),
        'date_exam': fields.datetime('Date', required=True),
        'subject_id': fields.many2one('school.subject', 'Subject', ondelete="cascade"),
        'weight': fields.integer('Weight', help="Define weight to calculate average"),
        'type': fields.selection([
            ('w1', 'Weight 1'),
            ('w2', 'Weight 2'),
            ('final', 'Final Exam'),
            ('average', 'Average'),
            ('conduct', 'Conduct'),
            ('overall', 'Overall'),
        ], 'Type', required=True, select=True),

        'semester': fields.selection([
            ('first', 'First Semester'),
            ('second', 'Second Semester'),
        ], 'Semester', required=True, select=True),
        'sequence': fields.integer('Sequence', help="Sort by order"),
        'company_id': fields.related('class_id', 'company_id', type='many2one', relation='res.company', string='School'),
    }

    _defaults = {
        'name': "/",
        'teacher_id': _get_default_teacher,
    }

    def create_multi(self, cr, uid, moves, context=None):
        if context is None:
            context = {}
        move_ids = []
        for move in moves:
            move_id = self.create(cr, uid, move, context=context)
            move_ids.append(move_id)

        return move_ids

    def write_multi(self, cr, uid, moves, context=None):
        if context is None:
            context = {}
        for move in moves:
            if move.has_key('id'):
                self.write(cr, uid, [move['id']], move, context=context)

class school_schedule(osv.osv):
    _name = 'school.schedule'

    _columns = {
        'name': fields.char('Name'),
        'class_id': fields.many2one('school.class', 'Class', required=True, ondelete="cascade"),
        'semester': fields.selection([
            ('first', 'First Semester'),
            ('second', 'Second Semester'),
        ], 'Semester', required=True, select=True),
        'lines': fields.one2many('school.schedule.line', 'schedule_id', 'Schedulle Lines'),
        'company_id': fields.related('class_id', 'company_id', relation='res.company', type='many2one', string='School'),
    }

    _defaults = {
        'name': '/',
    }

    def _check_duplicate(self, cr, uid, ids, context=None):
        for schedule in self.browse(cr, uid, ids, context=None):
            domain = [
                ('class_id', '=', schedule.class_id.id),
                ('semester', '=', schedule.semester),
                ('company_id','=', schedule.company_id.id)
            ]
            count = self.search_count(cr, uid, domain, context=context)
            if count>1:
                return False
        return True

    _constraints = [
        (_check_duplicate, 'One schedule allowed only for a semester of class',['class_id','semester','company_id']),
    ]


class school_schedule_line(osv.osv):
    _name = 'school.schedule.line'

    _columns = {
        'name': fields.char('Name'),
        'schedule_id': fields.many2one('school.schedule', 'Schedule Ref', required=True, ondelete='cascade', select=True),
        'week_day': fields.selection([
            ('mon', 'Monday'),
            ('tue', 'Tuesday'),
            ('wed', 'Wednesday'),
            ('thu', 'Thursday'),
            ('fri', 'Friday'),
            ('sat', 'Saturday'),
            ('sun', 'Sunday'),
        ], 'Week Day', required=True, select=True),
        'class_id': fields.related('schedule_id', 'class_id', type='many2one', relation='school.class', store=True, string='Class', ondelete="cascade"),
        'subject_id': fields.many2one('school.subject', 'Subject', required=True, ondelete="cascade"),
        'teacher_id': fields.many2one('hr.employee', 'Teacher', required=True, domain="[('teacher','=',True)]", ondelete="cascade"),
        'begin': fields.datetime('Begin', required=True),
        'end': fields.datetime('End', required=True),
    }

    _defaults = {
        'name': '/',
    }


class im_chat_message(osv.Model):

    _inherit = 'im_chat.message'

    _columns = {
        'delay_time': fields.datetime('Delay Time'),
        'self_notify': fields.boolean("Is Self Notification"),
    }

    _defaults = {
        'self_notify': False,
    }

    def get_messages(self, cr, uid, uuid, last_id=False, limit=20, context=None):
        """ get messages (id desc) from given last_id in the given session """
        Session = self.pool['im_chat.session']
        if Session.is_in_session(cr, uid, uuid, uid, context=context):
            domain = [("to_id.uuid", "=", uuid),("delay_time", '=', None)]
            if last_id:
                domain.append(("id", "<", last_id));
            return self.search_read(cr, uid, domain, ['id', 'create_date','to_id','from_id', 'type', 'message'], limit=limit, context=context)
        return False

    def post_delay(self, cr, uid, from_uid, uuid, message_type, message_content, delayTime, context=None):
        """ post and broadcast a message, return the message id """
        message_id = False
        Session = self.pool['im_chat.session']
        session_ids = Session.search(cr, uid, [('uuid','=',uuid)], context=context)
        notifications = []
        for session in Session.browse(cr, uid, session_ids, context=context):
            vals = {
                "from_id": from_uid,
                "to_id": session.id,
                "type": message_type,
                "message": _('You have just sent a timer message.'),
                "self_notify": True,
            }
            # Create self notification first
            message_id = self.create(cr, uid, vals, context=context)
            # broadcast it to channel (anonymous users) and users_ids
            data = self.read(cr, uid, [message_id], ['from_id', 'to_id', 'create_date', 'type', 'message'], context=context)[0]
            notifications.append([uuid, data])
            notifications.append([(cr.dbname, 'im_chat.session', uid), data])
            self.pool['bus.bus'].sendmany(cr, uid, notifications)

            # build the timer message
            vals = {
                "from_id": from_uid,
                "to_id": session.id,
                "type": message_type,
                "message": message_content,
                "delay_time": delayTime,
            }
            # save it & broastcast later
            message_id = self.create(cr, uid, vals, context=context)

        return message_id

    def broadcast_delay(self, cr, uid, context=None):
        now = datetime.datetime.now().strftime(DATETIME_FORMAT)
        delay_ids = self.search(cr, SUPERUSER_ID, [('delay_time','<=', now)], context=context)
        if delay_ids and len(delay_ids) > 0:
            for message_id in delay_ids:
                notifications = []
                # broadcast it to channel (anonymous users) and users_ids
                data = self.read(cr, SUPERUSER_ID, [message_id], ['from_id', 'to_id', 'create_date', 'type', 'message'],
                                 context=context)[0]
                uuid = data['to_id']
                session_ids = self.pool['im_chat.session'].search(cr, SUPERUSER_ID, [('uuid','=', uuid)], context=context, limit=1)
                session_id = session_ids and session_ids[0] or None
                if session_id:
                    session = self.pool['im_chat.session'].browse(cr, SUPERUSER_ID, session_id, context=context)
                    notifications.append([uuid, data])
                    for user in session.user_ids:
                        notifications.append([(cr.dbname, 'im_chat.session', user.id), data])
                    self.pool['bus.bus'].sendmany(cr, uid, notifications)

            # Clear delaytime
            self.write(cr, SUPERUSER_ID, delay_ids, {'delay_time': None}, context=context)