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
    
class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    _columns = {
        'student': fields.boolean('Is a Student'),
        'parent': fields.boolean('Is a Parent'),
        'teacher': fields.boolean('Is a Teacher'),
        'parent_ids': fields.many2many('res.partner', 'parent_student_rel', 'parent_id', 'student_id', 'Parents',
                                        domain="[('parent','=',True)]"),
        'child_ids': fields.many2many('res.partner', 'student_parent_rel', 'student_id', 'parent_id', 'Childs',
                                       domain="[('student','=',True)]"),
    }


class school_scholarity(osv.osv):
    _name = 'school.scholarity'
    
    _columns = {
        'name': fields.char('Scholarity Year', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'date_start': fields.datetime('Start Date', required=True),
        'date_end': fields.datetime('End Date', required=True),
    }   
    
    
class school_class_group(osv.osv):
    _name = 'school.class.group'
    
    _columns = {
        'name': fields.char('Name', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list "),  
    }
    
class school_subject(osv.osv):
    _name = 'school.subject'
    
    _columns = {
        'name': fields.char('Name', required=True),
        'company_id':fields.many2one('res.company', 'School', domain="[('school','=',True)]"),
        'weight': fields.integer('Weight', help="Define weight to calculate average"),  
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list "),  
    }

class school_class(osv.osv):
    _name = 'school.class'
    
    _columns = {
        'name': fields.char('Name', required=True),
        'year_id':fields.many2one('school.scholarity', 'Year', required=True),
        'company_id':fields.many2one('res.company', 'School', required=True, domain="[('school','=',True)]"),
        'group_id':fields.many2one('school.class.group', 'Group', required=True),
        'teacher_id':fields.many2one('res.partner', 'Responsible', domain="[('teacher','=',True)]"),
        'student_ids':fields.many2many('res.partner', 'school_class_student_rel', 'class_id', 'student_id', 'Students', domain="[('student','=',True)]"),
    }
    
class school_exam(osv.osv):
    _name = 'school.exam'

    _columns = {
        'name': fields.char('Name', required=True),
        'state': fields.selection([
            ('draft', 'Draft Exam'),
            ('done', 'Done'),
        ], 'Status', readonly=True, copy=False, help="Gives the status of exam", select=True),
        'date_exam': fields.datetime('Date', required=True, readonly=True, select=True,
                                      states={'draft': [('readonly', False)]}, copy=False),
        'subject_id': fields.many2one('school.subject', 'Subject', required=True),
        'class_id': fields.many2one('school.class', 'Class', required=True),
        'weight': fields.integer('Weight', help="Define weight to calculate average"),
        'exam_line': fields.one2many('school.exam.line', 'exam_id', 'Exam Lines', readonly=True,
                                      states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                      copy=True),

    }

class school_exam_line(osv.osv):
    _name = 'school.exam.line'

    _columns = {
        'exam_id': fields.many2one('school.exam', 'Exam Ref', required=True, ondelete='cascade', select=True,
                                    readonly=True, states={'draft': [('readonly', False)]}),
        'name': fields.char('Name', required=True),
        'student_id': fields.many2one('res.partner', 'Student', domain=[('student', '=', True)],
                                      change_default=True, readonly=True, states={'draft': [('readonly', False)]},
                                      ondelete='restrict'),
        'mark': fields.float('Mark', readonly=True, states={'draft': [('readonly', False)]}),

         'state': fields.selection([
            ('draft', 'Draft Exam'),
            ('done', 'Done'),
        ], 'Status', readonly=True, copy=False, help="Gives the status of exam", select=True),
        'date_exam': fields.datetime('Date', required=True, readonly=True, select=True,
                                      states={'draft': [('readonly', False)]}, copy=False),
        'subject_id': fields.many2one('school.subject', 'Subject', required=True),
        'class_id': fields.many2one('school.class', 'Class', required=True),
        'weight': fields.integer('Weight', help="Define weight to calculate average"),

    }