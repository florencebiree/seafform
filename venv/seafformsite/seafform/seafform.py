# -*- coding: utf-8 -*-
###############################################################################
#       seafform/seafform.py
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
"""Seafform forms description"""

__author__ = "Florian Birée"
__version__ = "0.1"
__license__ = "GPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"
__revision__ = "$Revision: $"
__date__ = "$Date: $"

import os
import ezodf
import shutil
import time
import datetime
from tempfile import NamedTemporaryFile
from django.utils.translation import ugettext_noop 
from django.utils.translation import ugettext as _

HEADERS_ROW = 4 # number of headers row in ods files
#all_less_maxcount strategy doesn't work
# trying all_but_last, then all
#ezodf.config.set_table_expand_strategy('all_but_last')

class InvalidODS(Exception):
    """Raise when the ODS file doesn't respect the specification for Seafform
    """
    pass

class Field:
    """Base class for form fields"""
    
    def __init__(self, label, description=None, params=None, required=False, 
                       value=None):
        """Initialize a new field"""
        self.label = label
        self.description = description
        self.params = params
        self.required = required
        self.value = value
    
    def __repr__(self):
        if hasattr(self, 'ident'):
            ftype = self.ident
        else:
            ftype = 'Field'
        return '<{0}({1}){2}>'.format(
            ftype,
            self.label,
            ('*' if self.required else '')
        )

class TextField(Field):
    """Single-line text field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('text')

class LongTextField(Field):
    """Multiline text field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('longtext')

class ListField(Field):
    """List of choices field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('list')
    
    def __init__(self, *args):
        Field.__init__(self, *args)
        self.choices = [
            ch.strip() for ch in self.params.split(',')
        ]

class BooleanField(Field):
    """Checkbox field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('check')

    def __init__(self, *args):
        Field.__init__(self, *args)
        self.value = False

class BooleanTrueField(Field):
    """Checked checkbox field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('checked')
    
    def __init__(self, *args):
        Field.__init__(self, *args)
        self.value = True

class DateField(Field):
    """Date field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('date')

class NumberField(Field):
    """Number field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('number')

class StaticField(Field):
    """Non-editable field"""
    # Translators: field type for spreadsheet
    ident = ugettext_noop('static')

def field_of(ident):
    """Return the Field subclass corresponding to `ident`"""
    return [
        cls 
        for cls in Field.__subclasses__() 
        if (cls.ident == ident) or (_(cls.ident) == ident)
    ][0]

def untranslate(loc_val, raw_list, loc_list):
    """If loc_val in raw_list,
        return loc_val
    else:
        Return the raw value at the same position in raw_list than
        loc_val in loc_list
    """
    if loc_val in raw_list:
        return loc_val
    else:
        return raw_list[loc_list.index(loc_val)]

class SeafForm:
    """Build and fill a form from an OpenDocumentSpreadsheet file"""
    _availables_f_ident = (
        [cls.ident for cls in Field.__subclasses__()]
        +
        [_(cls.ident) for cls in Field.__subclasses__()]
    )

    def __init__(self, filepath, seaf=None, repo_id=None):
        """Initialize a form for the file `filepath`.

            If seaf is a Seafile instance, repo_id must be the
            Seafile identifier of the repository where `filepath` is.

            If seaf is None, load `filepath` from the local filesystem
        """
        # source properties
        self.filepath = filepath
        self.seaf = seaf
        self.repo_id = repo_id
        self.loaded = False

        # form properties
        self.title = None
        self.description = None
        self.fields = None
        self.data = None
        # Translators: ODS view mode
        self._view_as_values = (ugettext_noop('table'), ugettext_noop('form'))
        self._view_as_l10n = [_(v) for v in self._view_as_values]
        self.view_as = None # ('table' or 'form')
        # Translators: ODS edit, yes or no
        self._edit_values = (ugettext_noop('yes'), ugettext_noop('no'))
        self._edit_val10n = [_(v) for v in self._edit_values]
        self.edit = None
        
        # cached items
        self.mtime = None
        self._odsfile = None
        self._first_empty_row = None

    def __repr__(self):
        """Representation of the form"""
        if self.loaded:
            return "<SeafForm({0}:{1})>".format(self.filepath, self.title)
        else:
            return "<SeafForm({0}:unloaded)>".format(self.filepath)

    def load(self):
        """Load form data from the ODS file"""
        odsopener = self._seaf_open if self.seaf else self._local_open
        
        seaf_f = odsopener()
        # save spreadsheet into a temporary file
        with NamedTemporaryFile(delete=False) as tmpfile:
            shutil.copyfileobj(seaf_f, tmpfile)
            tmpname = tmpfile.name
        seaf_f.close()
        
        # open spreadsheet document
        self.odsfile = ezodf.opendoc(tmpname)
        # delete tmp file
        os.unlink(tmpname)
        
        
        # get the Data sheet
        try:
            datash = self.odsfile.sheets['Data']
        except KeyError:
            raise InvalidODS 
        
        # get Properties
        self.title = datash['A7'].value
        self.description = datash['A9'].value
        self.view_as = untranslate(
            datash['A11'].value,
            self._view_as_values,
            self._view_as_l10n
        )
        self.edit = ('yes' == (untranslate(
            datash['A13'].value,
            self._edit_values,
            self._edit_val10n
        )))
        
        # get fields
        self.fields = []
        for colid in range(1, datash.ncols()):
            # get column
            col = datash.column(colid)
            # get field data
            fname   = col[0].value
            fformat = col[1].value
            fparams = col[2].value
            fdesc   = col[3].value
            # col[4:] is data
            
            # build field object (if fformat is known)
            if fformat and fformat.strip('*') in self._availables_f_ident:
                frequired = (fformat.endswith('*'))
                FType = field_of(fformat.rstrip('*'))
                self.fields.append(FType(
                    fname, fdesc, fparams, frequired
                ))
        
        # get data
        self.data = []
        first_empy_row = self._get_first_empty_row(recompute=True)
        for rowid in range(HEADERS_ROW, first_empy_row):
            row = datash.row(rowid)
            row_data = []
            for celid in range(1, len(self.fields) + 1):
                val = row[celid].value
                if self.fields[celid-1].ident == 'date' and val:
                    try:
                        s_time = time.strptime(val, '%Y-%m-%d')
                    except ValueError:
                        pass # keep val as str
                    else:
                        val = datetime.date(*s_time[:3])
                row_data.append(val)
            self.data.append(row_data)
        
        # get mtime
        if self.seaf:
            s = self.seaf.stat_file(self.repo_id, self.filepath)
            self.mtime = float(s['mtime'])
        else:
            self.mtime = os.path.getmtime(self.filepath)
        
        self.loaded = True
    
    def _seaf_open(self):
        """Return an opened file-like object from Seafile"""
        return self.seaf.open_file(self.repo_id, self.filepath)

    def _local_open(self):
        """Return an opened file object from local filesystem"""
        return open(self.filepath, 'rb')
    
    def _get_first_empty_row(self, recompute=False):
        """Return the first empty row number
            if recompute, do not use the cached value
        """
        if self._first_empty_row is not None and not recompute:
            return self._first_empty_row
        
        # get the Data sheet
        try:
            datash = self.odsfile.sheets['Data']
        except KeyError:
            raise InvalidODS 
                
        # find the first empty row
        rowid = datash.nrows() - 1
        bcol = datash.column(1)
        for celid in reversed(range(HEADERS_ROW, datash.nrows())):
            if not bcol[celid].value:
                rowid = celid
            else:
                break
        for colid in range(1, datash.ncols()):
            # check if rowid is empty for all the row
            # go down until empty
            while (rowid < datash.nrows() and datash[rowid, colid].value):
                rowid += 1
        
        self._first_empty_row = rowid 
        return rowid
    
    def post(self, values, replace_row=None):
        """Post data from values into the ODS file

            values is the dict of {ident: value}
            optionaly replace values from the row `replace_row`
            
            WARNING: type and required verification must be done before
        """
        # get new mtime
        if self.seaf:
            s = self.seaf.stat_file(self.repo_id, self.filepath)
            new_mtime = float(s['mtime'])
        else:
            new_mtime = os.path.getmtime(self.filepath)
        # if mtime has changed:
        if self.mtime != new_mtime:
            self.load() # reload
        
        # get the Data sheet
        try:
            datash = self.odsfile.sheets['Data']
        except KeyError:
            raise InvalidODS 
        
        
        # save data in a new line        
        if replace_row is None:
            rowid = self._get_first_empty_row()
            self.data.append([])
            self._first_empty_row += 1
        else:
            rowid = replace_row
        
        # fill the row with values
        for colid in range(1, datash.ncols()):
            column = datash.column(colid)
            fname = column[0].value
            if fname in values and values[fname]:
                value = (1 if values[fname] is True else values[fname])
                try:
                    column[rowid].set_value(value)
                except IndexError:
                    # add row
                    datash.append_rows(1)
                    column = datash.column(colid)
                    column[rowid].set_value(value)
                try:
                    self.data[rowid - HEADERS_ROW][colid - 1] = value
                except IndexError:
                    self.data[rowid - HEADERS_ROW].append(value)
            else:
                try:
                    self.data[rowid - HEADERS_ROW][colid - 1] = None
                except IndexError:
                    self.data[rowid - HEADERS_ROW].append(None)
        
        if self.seaf:        
            # save spreadsheet into a temporary file
            with NamedTemporaryFile(delete=False) as tmpfile:
                # ezodf realy doesn't like file-like objects…
                tmpname = tmpfile.name
            self.odsfile.saveas(tmpname)
                
            # update distant file
            with open(tmpname, 'rb') as fileo:
                fid = self.seaf.update_file(self.repo_id, self.filepath, fileo)
            # unlink tmp file
            os.unlink(tmpname)
        else:
            # save spreadsheet into the local file
            self.odsfile.saveas(self.filepath)

    def get_values_from_data(self, row_id):
        """Build the dict of {'name': value} for row_id from self.data"""
        vals = {}
        for i, field in enumerate(self.fields):
            vals[field.label] = self.data[row_id - HEADERS_ROW][i]
        return vals
