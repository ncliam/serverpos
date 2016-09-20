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


class res_company(osv.osv):
    _inherit = 'res.company'
    
    _columns = {
        'school': fields.boolean('School'),
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
    
    _columns = {
        'name': fields.char('Scholarity Year', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'date_start': fields.datetime('Start Date', required=True),
        'date_end': fields.datetime('End Date', required=True),
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
    
    _columns = {
        'name': fields.char('Name', required=True),
        'year_id':fields.many2one('school.scholarity', 'Year', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'group_id':fields.many2one('school.class.group', 'Group', required=True),
        'teacher_id':fields.many2one('hr.employee', 'Responsible', domain="[('teacher','=',True)]"),
        'student_ids':fields.many2many('hr.employee', 'school_class_student_rel', 'class_id', 'student_id', 'Students', domain="[('student','=',True)]"),
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
        'class_id': fields.related('schedule_id', 'class_id', type='many2one', relation='school.class', store=True,
                                      string='Class'),
        'subject_id': fields.many2one('school.subject', 'Subject', required=True),
        'user_id': fields.many2one('res.users', 'Teacher', required=True),
        'begin': fields.datetime('Begin', required=True),
        'end': fields.datetime('End', required=True),

    }

    _defaults = {
        'name': '/',
    }