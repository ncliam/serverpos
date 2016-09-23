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

class res_user(osv.osv):
    _inherit = 'res.users'

    def _get_schools(self, cr, uid, context=None):

        school_ids = []
        res_user = self.pool.get('res.users')
        res_partner = self.pool.get('res.partner')

        user_id = res_user.browse(cr, uid, uid, context=context)
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


    def get_relate_schools(self, cr, uid, ids, name, args, context=None):
        res = {}
        for user_id in self.browse(cr, uid, ids, context=context):
            res[user_id.id] = self._get_schools(cr, user_id.id, context=context)
        return res

    _columns = {
        'school_ids': fields.function(get_relate_schools, relation='res.company', type='many2many',
                                           string='Related Schools', readonly=True),
    }


class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'children': fields.many2many('hr.employee', 'parent_student_rel', 'student_id', 'partner_id', 'Childs', readonly=True),
    }

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

        'class_ids': fields.many2many('school.class', 'school_class_student_rel', 'student_id', 'class_id', 'Classes',
                                        domain="[('active','=',True)]"),
    }

    _defaults = {
        'company_id': _get_default_company,
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        context = dict(context, mail_create_nosubscribe=True)
        return super(hr_employee, self).create(cr, uid, values, context=context)

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

    _columns = {
        'name': fields.char('Name'),
        'class_id': fields.many2one('school.class', 'Class', required=True),
        'user_id': fields.many2one('res.users', 'Teacher', required=True),
        'student_id': fields.many2one('hr.employee', 'Student',
                        domain=[('student', '=', True)], required=True, ondelete='restrict'),
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
        'company_id': fields.related('class_id', 'company_id', type='many2one', string='School'),
    }

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
        'company_id': fields.related('class_id', 'company_id', type='many2one', string='School'),
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