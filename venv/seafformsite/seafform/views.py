# -*- coding: utf-8 -*-
###############################################################################
#       seafform/views.py
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
"""Seafform views"""

__author__ = "Florian Birée"
__version__ = "0.1"
__license__ = "GPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"
__revision__ = "$Revision: $"
__date__ = "$Date: $"

from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from seafform.models import SeafileUser, Form
from seafform.forms import LoginForm
from seafform.seafile import Seafile, AuthError
from seafformsite.settings import SEAFILE_ROOT, TPL_URL

def index(request):
    """Main login view"""
    #TODO: whatif the seafile password change?
        # the user should with it's old password, and should be able to
        # enter its new password and resync
    justlogout = False
    autherror = False
    seaf_root = SEAFILE_ROOT
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = LoginForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(username=email, password=password)
            # if known user:
            if user is not None and user.is_active:
                login(request, user)
                # login, -> /private/
                return HttpResponseRedirect('/private/')
            elif user is not None: # not active
                autherror = True
            else:
                # try to connect to seafile using credentials
                seaf = Seafile(seaf_root)
                try:
                    seaf.authenticate(email, password)
                except AuthError:
                    autherror = True
                else:
                    token = seaf.token
                    # create new user, save the token
                    user = User.objects.create_user(email, email, password)
                    user.save()
                    seafuser = SeafileUser(user=user, seafroot=seaf_root,
                                           seaftoken=token)
                    seafuser.save()
                    # login
                    user2 = authenticate(username=email, password=password)
                    login(request, user2)
                    # -> /private/
                    return HttpResponseRedirect('/private/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = LoginForm()
    
    if 'action' in request.GET:
        justlogout = (request.GET['action'] == 'logout')

    return render(request, 'seafform/index.html', {
        'loginform': form,
        'autherror': autherror,
        'justlogout': justlogout,
        'seaf_root': seaf_root,
    })

@login_required(login_url='index')
def private(request):
    """Home of private pages"""
    return render(request, 'seafform/private.html', {
        'user': request.user,
        'forms': None,
        'tplurl': TPL_URL,
        #'forms': Form.objects.get(owner=request.user),
    })

def logout_view(request):
    """Just… log out"""
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect('/?action=logout')

def new(request):
    pass
