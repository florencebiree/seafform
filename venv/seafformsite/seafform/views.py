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
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from seafform.models import SeafileUser, Form
from seafform.forms import LoginForm, NewFormForm
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

@login_required(login_url='index')
def new(request):
    """Create a new form"""
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NewFormForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # create the form and redirect
            pass
    else:
        form = NewFormForm()
    
    return render(request, 'seafform/new.html', {
        'user': request.user,
        'newformform': form,
    })

# utility function
def parse(seafpath):
    """Return a seafile path under the form :
            {
                'repo_name':
                'path'
            }
        the root of all libraries has repo_id == None 
    """
    seafpath = seafpath.strip('/').split('/')
    if seafpath == ['']:
        # root
        return {'repo_name': None, 'repo_id': None, 'path': None}
    else:
        return {
            'repo_name': seafpath[0],
            'path': '/' + '/'.join(seafpath[1:])
        }

def repo_id_from_name(seaf, repo_name):
    """Return the repo_id from a repo_name"""
    repo_list = seaf.list_repos()
    for repo in repo_list:
        if repo['name'] == repo_name:
            return repo['id']
    return None

@csrf_exempt # the javascript lib user POST, but no data changes here
@login_required(login_url='index')
def lsdir(request):
    """Return the list of files in a Seafile directory"""
    if request.method == 'POST':
        path = request.POST['dir']
        # Connect to Seafile
        seafu = request.user.seafileuser
        seaf = Seafile(seafu.seafroot)
        seaf.authenticate(request.user.email, token=seafu.seaftoken, validate=False)
        # list the directory
        parsed_path = parse(path)
        # root of all libraries
        if parsed_path['repo_name'] is None:
            repo_list = seaf.list_repos()
            result = [
                {
                    'name': repo['name'],
                    'type': repo['type'],
                    'path': '/%s/' % repo['name'],
                } for repo in repo_list 
            ]
        else:
            repo_name, dirpath = parsed_path['repo_name'], parsed_path['path']
            repo_id = repo_id_from_name(seaf, repo_name)
            ls = seaf.list_dir(repo_id, dirpath)
            result = [
                {
                    'name': node['name'],
                    'type': node['type'],
                    'path': (
                        path.rstrip('/') + '/' + node['name'] + 
                        ('/' if node['type'] == 'dir' else '')
                    )
                } for node in ls
                  if (node['type'] == 'dir' or node['name'].endswith('.ods'))
            ]
        return render(request, 'seafform/lsdir.html', {'result': result})
    raise Http404("Bad request method")

        
