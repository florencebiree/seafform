# -*- coding: utf-8 -*-
###############################################################################
#       seafformsite/urls.py
#       
#       Copyright © 2017, Flo Birée <flo@biree.name>
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

__author__ = "Flo Birée"
__version__ = "0.2"
__license__ = "AGPLv3"
__copyright__ = "Copyright © 2017, Flo Birée <flo@biree.name>"

from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('seafform.urls')),
]
