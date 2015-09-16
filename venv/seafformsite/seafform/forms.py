# -*- coding: utf-8 -*-
###############################################################################
#       seafform/forms.py
#       
#       Copyright © 2015, Florian Birée <florian@biree.name>
#       
#       This file is a part of seafform.
#       
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <http://www.gnu.org/licenses/>.
#       
###############################################################################
"""Seafform Django forms description"""

__author__ = "Florian Birée"
__version__ = "0.1"
__license__ = "GPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"
__revision__ = "$Revision: $"
__date__ = "$Date: $"

from django import forms
import seafform.seafform as seafform

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    # autofocus to email
    email.widget.attrs.update({'autofocus' : 'autofocus'})

class DjForm(forms.Form):
    
    required_css_class = 'required'
    
    rowid = forms.CharField(widget=forms.HiddenInput, initial='newrow')
    
    def __init__(self, *args, **kwargs):
        """Add one more arguments:
            fieldlist: a seafform.Fields list
        """
        fieldlist = kwargs.pop('fieldlist')
        super(DjForm, self).__init__(*args, **kwargs)
        
        firstfield = None
        
        for field in fieldlist:
            stdparams = {
                'label': field.label,
                'required': field.required,
                'help_text': field.description,
            }
            if isinstance(field, seafform.TextField):
                self.fields[field.label] = forms.CharField(**stdparams)
            elif isinstance(field, seafform.LongTextField):
                params = stdparams.copy()
                params.update(widget = forms.Textarea)
                self.fields[field.label] = forms.CharField(**params)
            elif isinstance(field, seafform.ListField):
                params = stdparams.copy()
                params.update(choices = ((c, c) for c in field.choices))
                self.fields[field.label] = forms.ChoiceField(**params)
            elif isinstance(field, seafform.BooleanField):
                params = stdparams.copy()
                params.update(initial = False)
                self.fields[field.label] = forms.BooleanField(**params)
            elif isinstance(field, seafform.BooleanTrueField):
                params = stdparams.copy()
                params.update(initial = True)
                self.fields[field.label] = forms.BooleanField(**params)
            elif isinstance(field, seafform.DateField):
                self.fields[field.label] = forms.DateField(**stdparams)
            elif isinstance(field, seafform.NumberField):
                self.fields[field.label] = forms.FloatField(**stdparams)
            
            if firstfield is None:
                firstfield = self.fields[field.label]
        
        # add autofocus to the first one
        firstfield.widget.attrs.update({'autofocus' : 'autofocus'})
