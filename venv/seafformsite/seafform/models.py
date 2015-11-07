# -*- coding: utf-8 -*-
###############################################################################
#       seafform/models.py
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
"""Seafform forms description"""

__author__ = "Florian Birée"
__version__ = "0.2"
__license__ = "AGPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.urlresolvers import reverse
from urllib.parse import urljoin

class SeafileUser(models.Model):
    """Profile class for user"""
    user = models.OneToOneField(User)
    seafroot = models.URLField()
    seaftoken = models.CharField(max_length=40)
    
    def __repr__(self):
        return "<SeafileProfile(%s)>" % self.user.email

class Form(models.Model):
    """Represent a Seafform"""
    owner = models.ForeignKey(User)
    filepath = models.CharField(max_length=256)
    repoid = models.CharField(max_length=40)
    reponame = models.CharField(max_length=256)
    formid = models.SlugField(max_length=40, primary_key=True)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    creation_datetime = models.DateTimeField(auto_now_add=True)
    public = models.BooleanField(default=False)

    def __repr__(self):
        return "<Form(%s, %s)>" % (self.title, self.owner.email)

    def get_absolute_url(self):
        """Return the public url of the form"""
        return urljoin(settings.ROOT_URL, reverse('form', args=(self.formid,)))
