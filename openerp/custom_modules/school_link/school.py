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
        'student': fields.boolean('Student'),
        'parent': fields.boolean('Parent'),
        'teacher': fields.boolean('Teacher'),        
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
        'group_id': fields.integer('Sequence', help="Gives the sequence order when displaying a list "),
        'teacher_id':fields.many2one('res.partner', 'Responsible', domain="[('teacher','=',True)]"),
        'student_ids':fields.many2many('res.partner', 'school_class_student_rel', 'class_id', 'student_id', 'Students', domain="[('student','=',True)]"),
    }
    
