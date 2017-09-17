# -*- coding: utf-8 -*-
###############################################################################
#       seafform/views.py
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
"""Seafform views"""

__author__ = "Florian Birée"
__version__ = "0.2"
__license__ = "AGPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"

import os
from urllib.parse import quote, unquote
import itertools
from django.utils.text import slugify
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from seafform.models import SeafileUser, Form
from seafform.forms import LoginForm, DjForm
from seafform.seafile import Seafile, AuthError, APIError
from seafform.seafform import SeafForm, HEADERS_ROW
from django.conf import settings

def _log(request, email, password, nextview):
    """ Authenticate or create a new account """
    seaf_root = settings.SEAFILE_ROOT
    user = authenticate(username=email, password=password)
    # if known user:
    if user is not None and user.is_active:
        login(request, user)
        # login, -> nexturl
        return HttpResponseRedirect(reverse(nextview))
    elif user is not None: # not active
        raise AuthError
    else:
        # try to connect to seafile using credentials
        seaf = Seafile(seaf_root, verifycerts=settings.VERIFYCERTS)
        seaf.authenticate(email, password) # may raise AuthError
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
        # -> nextview
        return HttpResponseRedirect(reverse(nextview))

def index(request):
    """Main login view"""
    #TODO: whatif the seafile password change?
        # the user should with it's old password, and should be able to
        # enter its new password and resync
    justlogout = False
    autherror = False
       
    # if authenticated, redirect to /private and no public forms
    if not settings.ALLOW_PUBLIC and request.user.is_authenticated():
        return HttpResponseRedirect(reverse('private'))
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = LoginForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            nextstep = (
                'index'
                if (settings.ALLOW_PUBLIC and settings.PUBLIC_NEED_AUTH) 
                else 'private'
            )
            
            try:
                return _log(request, email, password, nextstep)
            except AuthError:
                autherror = True

    # if a GET (or any other method) we'll create a blank form
    else:
        form = LoginForm()
    
    if 'action' in request.GET:
        justlogout = (request.GET['action'] == 'logout')

    return render(request, 'seafform/index.html', {
        'loginform': form,
        'autherror': autherror,
        'justlogout': justlogout,
        'seaf_root': settings.SEAFILE_ROOT,
        'allow_public': settings.ALLOW_PUBLIC,
        'public_needauth': settings.PUBLIC_NEED_AUTH,
        'authenticated': request.user.is_authenticated(),
        'public_forms': Form.objects.filter(public=True).\
                              order_by('-creation_datetime'),
        'show_public': (
            settings.ALLOW_PUBLIC and ( 
                request.user.is_authenticated()
                or 
                not settings.PUBLIC_NEED_AUTH
            )),
    })

@login_required(login_url='index')
def private(request):
    """Home of private pages"""
    newform = None
    delformtitle = None
    deleted = None
    if request.method == 'POST': #delete
        deleteid = request.POST.get('deleteid', '')
        try:
            tobedeleted = Form.objects.get(formid=deleteid, owner=request.user)
        except Form.DoesNotExist:
            # do nothing
            pass
        else:
            # delete, redirect plus message
            deleted = tobedeleted.title
            tobedeleted.delete()
    
    if 'newform' in request.GET:
        try:
            newform = Form.objects.get(formid=request.GET['newform'], 
                                        owner=request.user)
        except Form.DoesNotExist:
            pass
        
    return render(request, 'seafform/private.html', {
        'user': request.user,
        'forms': None,
        'tplurl': settings.TPL_URL,
        'forms': Form.objects.filter(owner=request.user).\
                              order_by('-creation_datetime'),
        'newform': newform,
        'deleted': deleted,
        'allow_public': settings.ALLOW_PUBLIC,
    })

def logout_view(request):
    """Just… log out"""
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect(reverse('index') + '?action=logout')

@login_required(login_url='index')
def new(request):
    """Create a new form"""
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        path = unquote(request.POST.get('path', ''))
        #print('new/path=' + path)
        if path.endswith('.ods'):
            if settings.LOCAL:
                filepath = os.path.join(settings.LOCAL_ROOT, path.lstrip('/'))
                seaf = None
                repoid = 'LOCAL'
                reponame = 'LOCAL'
            else:
                # Connect to Seafile
                seafu = request.user.seafileuser
                seaf = Seafile(seafu.seafroot, verifycerts=settings.VERIFYCERTS)
                seaf.authenticate(request.user.email, token=seafu.seaftoken, validate=False)
                # retreive path info
                parsed_path = parse(path)
                filepath = parsed_path['path']
                repoid = repo_id_from_name(seaf, parsed_path['repo_name'])
                reponame = parsed_path['repo_name']
            # load the form
            seafform = SeafForm(filepath, seaf, repoid)
            seafform.load()
            # create the slug/formid
            max_length = Form._meta.get_field('formid').max_length
            formid = orig = slugify(seafform.title)[:max_length]
            
            for x in itertools.count(1):
                if not Form.objects.filter(formid=formid).exists():
                    break
            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            formid = "%s-%d" % (orig[:max_length - len(str(x)) - 1], x)
            
            # add the new form
            newform = Form(
                owner = request.user,
                filepath = filepath,
                repoid = repoid,
                reponame = reponame,
                formid = formid,
                title = seafform.title,
                creation_datetime = timezone.now(),
                description = seafform.description,
                public = seafform.public,
            )
            newform.save()
            # Redirect + message
            return HttpResponseRedirect(reverse('private') + '?newform=' + formid)
    
    return render(request, 'seafform/new.html', {
        'user': request.user,
        'allow_public': settings.ALLOW_PUBLIC,
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
        # dirty hack
        path = unquote(unquote(request.POST['dir'], encoding='latin9'))
        if settings.LOCAL:
            abspath = settings.LOCAL_ROOT.rstrip('/') +  path
            result = [
                {
                    'name': name,
                    'type': (
                        'dir' if os.path.isdir(os.path.join(abspath, name))
                        else 'file'),
                    'path': (
                        os.path.join(abspath, name)[len(settings.LOCAL_ROOT.rstrip('/')):] +
                        ('/' if os.path.isdir(os.path.join(abspath, name)) else '')
                    )
                } for name in os.listdir(abspath)
                  if (os.path.isdir(os.path.join(abspath, name)) 
                        or name.endswith('.ods'))
            ]
        else:
            # Connect to Seafile
            seafu = request.user.seafileuser
            seaf = Seafile(seafu.seafroot, verifycerts=settings.VERIFYCERTS)
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
                        'path': quote('/%s/' % repo['name']),
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
                        'path': quote( (
                            path.rstrip('/') + '/' + node['name'] + 
                            ('/' if node['type'] == 'dir' else '') )
                        )
                    } for node in ls
                    if (node['type'] == 'dir' or node['name'].endswith('.ods'))
                ]
        return render(request, 'seafform/lsdir.html', {'result': result})
    raise Http404("Bad request method")

def _update_form_attr(dbform, seafform):
    """Update db attributes from ODS file"""
    needupdate = False
    if seafform.title != dbform.title:
        dbform.title = seafform.title
        needupdate = True
    if seafform.public != dbform.public:
        dbform.public = seafform.public
        needupdate = True
    if needupdate:
        dbform.save()

def formview(request, formid):
    """Display a public form"""
    justaddedrow = None
    # get the form object
    try:
        form = Form.objects.get(formid=formid)
    except Form.DoesNotExist:
        raise Http404
    # get the seafform object (Seafile connexion)
    if settings.LOCAL:
        seaf = None
    else:
        seafu = form.owner.seafileuser
        seaf = Seafile(seafu.seafroot, verifycerts=settings.VERIFYCERTS)
        seaf.authenticate(form.owner.email, token=seafu.seaftoken, validate=False)
    seafform = SeafForm(form.filepath, seaf, form.repoid)
    try:
        seafform.load()
    except APIError:
        raise Http404
        
    _update_form_attr(form, seafform)
    
    # build the corresponding DjForm()
    if request.method == 'POST':
        results = False
        # results management
        djform = DjForm(request.POST, fieldlist=seafform.fields)
        if djform.is_valid():
            # check if we replace a row
            if seafform.edit and djform.cleaned_data['rowid'] != 'newrow':
                replace_row = int(djform.cleaned_data['rowid'])
                justaddedrow = replace_row - HEADERS_ROW
            else:
                replace_row = None
                justaddedrow = seafform._first_empty_row - HEADERS_ROW
            # save data
            seafform.post(djform.cleaned_data, replace_row)
            
            # if valid form and form and not edit:
            if seafform.view_as == 'form' and not seafform.edit:
                # redirect to thanks
                return HttpResponseRedirect(reverse('thanks',args=(formid,)))
            elif seafform.view_as == 'form':
                return HttpResponseRedirect(
                    reverse('form',args=(formid,)) + '?results'
                )
                #results = True # redirect to table
                
            # clean fields
            djform = DjForm(fieldlist=seafform.fields)
    else:
        djform = DjForm(fieldlist=seafform.fields)
        results = ('results' in request.GET)
        
    if seafform.view_as == 'form' and not results:
        # form view
        return render(request, 'seafform/form_as_form.html', {
            'seafform': seafform,
            'modelform': form,
            'djform': djform,
        })
        
    elif seafform.view_as == 'table' or (results and seafform.edit):
        # hightlight first column if static field
        first_is_static = (seafform.fields[0].ident == 'static')
        # compute some results
        max_chk = 0
        computations = []
        for colid, field in enumerate(seafform.fields):
            # if check boxe, number of checks
            if field.ident.startswith('check'):
                res = sum(row[colid] for row in seafform.data if row[colid])
                max_chk = max(max_chk, res)
                computations.append(res)
            # if number, the sum
            elif field.ident == 'number':
                computations.append(sum(
                    row[colid] for row in seafform.data if row[colid]
                ))
            else:
                computations.append(None)
        # columns with a star
        max_chk_column = []
        for colid, field in enumerate(seafform.fields):
            if field.ident.startswith('check') and computations[colid] == max_chk:
                max_chk_column.append(colid)
        
        # table view    
        return render(request, 'seafform/form_as_table.html', {
            'seafform': seafform,
            'modelform': form,
            'djform': djform,
            'justaddedrow': justaddedrow,
            'first_is_static': first_is_static,
            'computations': computations,
            'max_chk_column': max_chk_column,
        })

    raise Http404

def formrowedit(request, formid, rowid):
    """Generate a form to edit rowid in formid"""
    rowid = int(rowid) + HEADERS_ROW
    # get the form object
    try:
        form = Form.objects.get(formid=formid)
    except Form.DoesNotExist:
        raise Http404
    # get the seafform object (Seafile connexion)
    if settings.LOCAL:
        seaf = None
    else:
        seafu = form.owner.seafileuser
        seaf = Seafile(seafu.seafroot, verifycerts=settings.VERIFYCERTS)
        seaf.authenticate(form.owner.email, token=seafu.seaftoken, validate=False)
    seafform = SeafForm(form.filepath, seaf, form.repoid)
    seafform.load()
    # create the django form for a specific row
    initials = seafform.get_values_from_data(rowid)
    initials['rowid'] = rowid
    djform = DjForm(
        initials,
        fieldlist=seafform.fields
    )
    return render(request, 'seafform/rowedit.html', {
        'seafform': seafform,
        'djform': djform,
        'modelform': form,
        'rowid': rowid - HEADERS_ROW,
    })

def thanks(request, formid):
    """Display the Thanks page"""
    # get the form object
    try:
        form = Form.objects.get(formid=formid)
    except Form.DoesNotExist:
        raise Http404
    return render(request, 'seafform/thanks.html', {
        'seafform': form,
    })

