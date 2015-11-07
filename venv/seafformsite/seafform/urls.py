# -*- coding: utf-8 -*-
###############################################################################
#       seafform/urls.py
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
"""Seafform URL dispatcher"""

__author__ = "Florian Birée"
__version__ = "0.2"
__license__ = "AGPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"

from django.conf.urls import patterns, url

from seafform import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'), 
    url(r'^private/$', views.private, name='private'),
    url(r'^private/logout/$', views.logout_view, name='logout'),
    url(r'^private/new/$', views.new, name='new'),
    url(r'^private/lsdir/$', views.lsdir, name='lsdir'),
    url(r'^form/(?P<formid>[^/]*)/$', views.formview, name='form'),
    url(r'^form/(?P<formid>[^/]*)/thanks/$', views.thanks, name='thanks'),
    url(r'^form/(?P<formid>[^/]*)/(?P<rowid>\d*)/$', views.formrowedit, name='rowedit'),
)
