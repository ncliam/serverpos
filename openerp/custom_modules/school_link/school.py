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
from openerp import SUPERUSER_ID
import datetime
from ast import literal_eval

class email_template(osv.osv):
    _inherit = "email.template"

    def _get_default_gateway(self, cr, uid, context=None):
        gateway_id = self.pool.get('sms.smsclient').search(cr, uid, [], context=context, limit=1)
        if not gateway_id:
            raise osv.except_osv(_('Error!'), _('There is no default gateway for the current user!'))
        return gateway_id[0]

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
                    'company_ids': [(6, 0, [company_id.id])],
                }
                self.pool.get("res.users").write(cr, SUPERUSER_ID, uid, user_data, context=context)

        else:
            raise osv.except_osv(_('error!'), _("Invalid school selected"))

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

    
    _columns = {
        'school': fields.boolean('School'),
        'children': fields.function(get_study_child, relation='hr.employee', type='many2many', string='Childs in study', readonly=True),
    }


class hr_employee(osv.osv):
    _inherit = "hr.employee"

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id

    _columns = {
        'last_name': fields.char('Last Name'),
        'home_town': fields.char('Home town'),
        'home_address': fields.char('Home Address'),
        'teacher': fields.boolean('Is a Teacher'),
        'student': fields.boolean('Is a Student'),
        'parent_ids': fields.many2many('res.partner', 'parent_student_rel', 'partner_id', 'student_id', 'Parents'),
        'class_ids': fields.many2many('school.class', 'school_class_student_rel', 'student_id', 'class_id', 'Classes', domain="[('active','=',True)]"),
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
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'date_start': fields.datetime('Start Date', required=True),
        'date_end': fields.datetime('End Date', required=True),
        'active': fields.function(_is_active, store=False, string='Active', type='boolean'),
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
    
    _columns = {
        'name': fields.char('Name', required=True),
        'year_id':fields.many2one('school.scholarity', 'Year', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'group_id':fields.many2one('school.class.group', 'Group', required=True),
        'teacher_id':fields.many2one('hr.employee', 'Responsible', domain="[('teacher','=',True)]"),
        'student_ids':fields.many2many('hr.employee', 'school_class_student_rel', 'class_id', 'student_id', 'Students', domain="[('student','=',True)]"),
        'active': fields.related('year_id', 'active', type='boolean', string='Active'),
        'teacher_ids': fields.function(_get_all_teachers, relation='hr.employee', type='many2many', string='Teachers',readonly=True),
        'parent_ids': fields.function(_get_all_parents, relation='res.partner', type='many2many', string='Parents', readonly=True),
    }

    _defaults = {
        'company_id': _get_default_company,
    }
    

class school_exam_move(osv.osv):
    _name = 'school.exam.move'

    def _get_default_teacher(self, cr, uid, context=None):
        teacher_ids = self.pool.get('hr.employee').search(cr, uid, [('teacher', '=', True), ('user_id', "=", uid)],context=context)
        return teacher_ids and teacher_ids[0]

    _columns = {
        'name': fields.char('Name'),
        'class_id': fields.many2one('school.class', 'Class', required=True),
        'teacher_id': fields.many2one('hr.employee', 'Teacher', required=True, domain=[('teacher', '=', True)]),
        'student_id': fields.many2one('hr.employee', 'Student', required=True, domain=[('student', '=', True)]),
        'mark': fields.float('Mark'),
        'date_exam': fields.datetime('Date', required=True),
        'subject_id': fields.many2one('school.subject', 'Subject', required=True),
        'weight': fields.integer('Weight', help="Define weight to calculate average"),
        'type': fields.selection([
            ('w1', 'Weight 1'),
            ('w2', 'Weight 2'),
            ('final', 'Final Exam'),
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
        'class_id': fields.many2one('school.class', 'Class', required=True),
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
        'class_id': fields.related('schedule_id', 'class_id', type='many2one', relation='school.class', store=True, string='Class'),
        'subject_id': fields.many2one('school.subject', 'Subject', required=True),
        'teacher_id': fields.many2one('hr.employee', 'Teacher', required=True, domain="[('teacher','=',True)]"),
        'begin': fields.datetime('Begin', required=True),
        'end': fields.datetime('End', required=True),
    }

    _defaults = {
        'name': '/',
    }