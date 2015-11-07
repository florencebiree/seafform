# -*- coding: utf-8 -*-
###############################################################################
#       seafform/forms.py
#       
#       Copyright © 2015, Florian Birée <florian@biree.name>
#       
#       This file is a part of seafform.
#       
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU Affero General Public License as 
#       published by the Free Software Foundation, either version 3 of the 
#       License, or (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU Affero General Public License for more details.
#       
#       You should have received a copy of the GNU Affero General Public License
#       along with this program.  If not, see <http://www.gnu.org/licenses/>.
#       
###############################################################################
"""Seafform Django forms description"""

__author__ = "Florian Birée"
__version__ = "0.2"
__license__ = "AGPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"

from django import forms
from django.forms.extras.widgets import SelectDateWidget
import seafform.seafform as seafform

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    # autofocus to email
    email.widget.attrs.update({'autofocus' : 'autofocus'})

class DjForm(forms.Form):
    
    required_css_class = 'required'

    rowid = forms.CharField(widget=forms.HiddenInput, initial='newrow')
    rowid.isstatic = False
    
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
            djfield = None
            if isinstance(field, seafform.TextField):
                djfield = forms.CharField(**stdparams)
            elif isinstance(field, seafform.LongTextField):
                params = stdparams.copy()
                params.update(widget = forms.Textarea)
                djfield = forms.CharField(**params)
            elif isinstance(field, seafform.ListField):
                params = stdparams.copy()
                params.update(choices = ((c, c) for c in field.choices))
                djfield = forms.ChoiceField(**params)
            elif isinstance(field, seafform.BooleanField):
                params = stdparams.copy()
                params.update(initial = False)
                djfield = forms.BooleanField(**params)
            elif isinstance(field, seafform.BooleanTrueField):
                params = stdparams.copy()
                params.update(initial = True)
                djfield = forms.BooleanField(**params)
            elif isinstance(field, seafform.DateField):
                params = stdparams.copy()
                params.update(widget = SelectDateWidget)
                djfield = forms.DateField(**params)
                djfield.widget.attrs.update(
                    {'style': 'width: 32%; display: inline-block;'}
                )
            elif isinstance(field, seafform.NumberField):
                djfield = forms.FloatField(**stdparams)
            elif isinstance(field, seafform.StaticField):
                params = stdparams.copy()
                params.update(widget=forms.HiddenInput)
                params['required'] = False
                djfield = forms.CharField(**params)
                djfield.isstatic = True
            
            if djfield is not None:
                self.fields[field.label] = djfield
                if not hasattr(djfield, 'isstatic'):
                    djfield.isstatic = False
            
            if firstfield is None:
                firstfield = self.fields[field.label]
        
        # add autofocus to the first one
        firstfield.widget.attrs.update({'autofocus' : 'autofocus'})
