#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
#       seafsh.py
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
"""Seafile shell using the Seafile API wrapper"""

__author__ = "Florian Birée"
__version__ = "0.1"
__license__ = "GPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"
__revision__ = "$Revision: $"
__date__ = "$Date: $"

import os
import shutil
import shlex
import cmd
import json
from functools import wraps
from seafile import Seafile 
from seafile import SeafileError, NotAuthenticated, NotFound, InvalidPath
from seafform import SeafForm

class SeafBrowser:
    """Seafile file browser
    
        Parse seafile path under the form /library_name/path/to/a/file
        Cache file lists
        Keep a current state
    """
    
    def __init__(self, knownhosts):
        """Initialize the browser with a `knowhosts` directory"""
        self.knownhosts = knownhosts
        self.seaf = None
        self.repo_cache = []
        self.ls_cache = {} # {repo_id:{path: [{item}, {item}]}}
        self.cwd = None

    # repo and path operations

    def repo_id(self, repo_name):
        """Find a repo_id from repo_name"""
        if not self.seaf:
            raise NotAuthenticated
        if not self.repo_cache:
            self.repo_cache = self.seaf.list_repos()
        for repo in self.repo_cache:
            if repo['name'] == repo_name:
                return repo['id']
        raise NotFound

    def parse(self, seafpath):
        """Return the path under the form :
            {
                'repo_name':
                'repo_id':
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
                'repo_id': self.repo_id(seafpath[0]),
                'path': '/' + '/'.join(seafpath[1:])
            }
    
    def join(self, *args):
        """Join all component of args. Resolve parents components."""
        # check if absolute path
        absolute = args[0].startswith('/')
        # fully split the components
        base_comp = []
        for node in args:
            base_comp += node.strip('/').split('/')
        comp = []
        # resolve parents components
        for node in base_comp:
            if node == '..':
                comp = comp[:-1]
            elif node == '':
                pass # remove //
            else:
                comp.append(node)
        return '/' + '/'.join(comp)
        
    # connection
    
    def connect(self, hostdesc):
        """Connect a Seafile instance using an host description
        
            hostdesc = {'url':, 'email':, 'password':, 'token':,}
            
            if token is not None, use it instead of password to authenticate
        
        """
        self.seaf = Seafile(hostdesc['url'])
        self.seaf.ping()
        if hostdesc.get('token', None):
            self.seaf.authenticate(hostdesc['email'], token=hostdesc['token'])
        else:
            self.seaf.authenticate(hostdesc['email'], password=hostdesc['password'])
        ctx.seaf.auth_ping()
        # clear current path and cache
        self.cwd = '/'
        self.repo_cache = []
        self.ls_cache = {}

    # directory operations

    def ls(self, path=None):
        """Return the list of nodes (repo, dir, or files) in `path`.
        
            If `path` is None, return the list of nodes in the cwd.
            
            nodes are {
                'name':,
                'id':,
                'type': repo|dir|file,
            }
            
            Once checked on seafile, each dir listing is cached.
        """
        if path is None:
            path = self.cwd
        parsed_path = self.parse(self.join(path))
        # root of all libraries
        if parsed_path['repo_id'] is None:
            if not self.repo_cache:
                self.repo_cache = self.seaf.list_repos()
            return [
                {
                    'name': repo['name'],
                    'id': repo['id'],
                    'type': repo['type'],
                } for repo in self.repo_cache
            ]
        else:
            
            repo_id, dirpath = parsed_path['repo_id'], parsed_path['path']
            try:
                ls = self.ls_cache[repo_id][dirpath]
            except KeyError:
                ls = self.seaf.list_dir(repo_id, dirpath)
            if not repo_id in self.ls_cache:
                self.ls_cache[repo_id] = {}
            if not dirpath in self.ls_cache[repo_id]:
                self.ls_cache[repo_id][dirpath] = ls
        # TODO: put the right .. status
        return [{'name': '..', 'id': None, 'type': 'dir'}] + [
            {
                'name': node['name'],
                'id': node['id'],
                'type' : node['type'],
            } for node in ls
        ]
    
    def cd(self, path='/'):
        """Change the cwd to the directory `path`
        
            .. is the parent dir
            / is the root of all libraries
        """
        # if relative path, join it with cwd
        if not path.startswith('/'):
            path = self.join(self.cwd, path)
        
        # to check the existence of the new cwd, we try to 'ls()' it
        # (also optimize further ls() by caching)
        self.ls(path)
        
        # if no exceptions raised, made it the new cwd
        self.cwd = path
        
    # files operations
    def download(self, path, destination):
        """Download a file"""
        # if relative path, join it with cwd
        if not path.startswith('/'):
            path = self.join(self.cwd, path)
        parsed_path = self.parse(path)
        repo_id, filepath = parsed_path['repo_id'], parsed_path['path']
        filename = filepath.split('/')[-1]
        
        seaf_f = self.seaf.open_file(repo_id, filepath)
        with open(destination, 'wb') as out_f:
            shutil.copyfileobj(seaf_f, out_f)
        
        print('Downloaded ' + destination)
    
    def upload(self, localfile, path):
        """Upload the `localfile` to `path` in Seafile"""
        # if relative path, join it with cwd
        if not path.startswith('/'):
            path = self.join(self.cwd, path)
        
        parsed_path = self.parse(path)
        repo_id, parent = parsed_path['repo_id'], parsed_path['path']
        
        if repo_id is None:
            raise InvalidPath
        
        with open(localfile, 'rb') as fileo:
            fileid = self.seaf.upload_file(repo_id, parent, fileo)
        print('up, id =', fileid)
        # invalidate the cache of `path`
        try:
            del(self.ls_cache[repo_id][parent])
        except KeyError:
            pass
    
    def update(self, localfile, distfile):
        """Update the `localfile` to `distfile` in Seafile"""
        # if relative path, join it with cwd
        if not distfile.startswith('/'):
            distfile = self.join(self.cwd, distfile)
            
        parsed_path = self.parse(distfile)
        repo_id, filepath = parsed_path['repo_id'], parsed_path['path']
        
        if repo_id is None:
            raise InvalidPath
        
        with open(localfile, 'rb') as fileo:
            fileid = self.seaf.update_file(repo_id, filepath, fileo)
        print('updated, id =', fileid)
        
    def delete(self, path):
        """Delete a file or a directory"""
        # if relative path, join it with cwd
        if not path.startswith('/'):
            path = self.join(self.cwd, path)
        parsed_path = self.parse(path)
        repo_id, filepath = parsed_path['repo_id'], parsed_path['path']
        
        self.seaf.delete_file(repo_id, filepath)
        
        # invalidate the cache of `path/..`
        parent = self.join(path, '..')
        parent_path = self.parse(parent)['path']
        try:
            del(self.ls_cache[repo_id][parent_path])
        except KeyError:
            pass
    
    def stat(self, path):
        """Return data about a file or directory"""
        # if relative path, join it with cwd
        if not path.startswith('/'):
            path = self.join(self.cwd, path)
        parsed_path = self.parse(path)
        repo_id, filepath = parsed_path['repo_id'], parsed_path['path']
        
        return self.seaf.stat_file(repo_id, filepath)

class SeafFormCli:
    """SeafForm cli interface"""
    
    def __init__(self, ctx, path):
        """New seafForm cli interface"""
        self.ctx = ctx
        # if relative path, join it with cwd
        if not path.startswith('/'):
            path = self.ctx.join(self.ctx.cwd, path)
        self.path = path
        self.form = None
    
    def _load(self):
        """Load the form content"""
        parsed_path = self.ctx.parse(self.path)
        repo_id, filepath = parsed_path['repo_id'], parsed_path['path']
        
        self.form = SeafForm(filepath, self.ctx.seaf, repo_id)
        self.form.load()

    def print(self):
        """Print Form data"""
        if not self.form:
            self._load()
        
        print(self.form)
        print('Description:', self.form.description)
        print('View as:', self.form.view_as)
        print('Edit:', self.form.edit)
        print('Fields:', self.form.fields)

    def fill(self):
        """Fill form, return a dict of {fieldname: value}"""
        if not self.form:
            self._load()
        
        result = {}
        for f in self.form.fields:
            valid = False
            while not valid:
                if f.description:
                    print(f.description)
                print('[', f.ident, ']')
                if hasattr(f, 'choices'):
                    print(f.choices)
                value = input(f.label + ('*' if f.required else '') + ': ')
                # check validity
                if f.required and not value:
                    continue # not valid
                if not value:
                    # no required, so valid
                    if f.ident == 'check':
                        value = False
                    elif f.ident == 'checked':
                        value = True
                    valid = True
                elif f.ident == 'number':
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            continue #not valid
                    valid = True
                elif f.ident == 'check' or f.ident == 'checked':
                    if value == 'True':
                        value = True
                    elif value == 'False':
                        value = False
                    else:
                        continue
                    valid = True
                elif f.ident == 'list':
                    if value not in f.choices:
                        continue
                    valid = True
                else:
                    valid = True
            result[f.label] = value
            print('-'*40)
        
        return result
    
    def post(self, result):
        """Post a filled form"""
        if not self.form:
            self._load()
        
        self.form.post(result)

def seaferr_protected(f):
    """Decorator to catch Seafile errors"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SeafileError as err:
            print(err)
    return wrapper

class SeafileShell(cmd.Cmd):
    intro = 'Welcome to the Seafile shell.   Type help or ? to list commands.\n'
    prompt = '(seafsh)$ '
    
    def __init__(self, browser):
        cmd.Cmd.__init__(self)
        self.ctx = browser
    
    def _update_prompt(self):
        """Update the prompt according to ctx"""
        if self.ctx.seaf is None:
            self.prompt = '(seafsh)$ '
        elif self.ctx.cwd is None:
            self.prompt = '(%s)$ ' % self.ctx.seaf.email
        else:
            self.prompt = '(%s)%s$ ' % (
                self.ctx.seaf.email,
                self.ctx.cwd
            )
    
    def do_exit(self, args=None):
        """Exit the shell"""
        return True
    
    def do_connect(self, hostname):
        """Connect and authenticate to `hostname`"""
        try:
            hostdesc = ctx.knownhosts[hostname]
        except KeyError as err:
            print('Unknown hostname: ' + str(err))
            return
        self.ctx.connect(hostdesc)
        print('auth, token=', ctx.seaf.token)
        self._update_prompt() 
    
    def complete_connect(self, text, line, begidx, endidx):
        """Completion for connect"""
        # return all hostnames starting with text
        return [
            hostname
            for hostname in self.ctx.knownhosts
            if hostname.startswith(text)
        ]
    
    def completedefault(self, text, line, begidx, endidx):
        """Completion for non-specific commands, provide file-system completion"""        
        # get the basepath for completion
        line = line[:begidx]
        if line.endswith('/'):
            # last part of line is part of basepath
            path = shlex.split(line)[-1]
            if path.startswith('/'):
                # absolute
                basepath = path
            else:
                # relative
                basepath = self.ctx.join(self.ctx.cwd, path)
        else:
            basepath = self.ctx.cwd
                
        return [
            (node['name'] + ('' if node['type'] == 'file' else '/'))
            for node in self.ctx.ls(basepath)
            if node['name'].startswith(text)
        ]
    
    @seaferr_protected
    def do_ls(self, *args):
        """List files or repo in the current place"""
        if not args[0]:
            path = self.ctx.cwd
        else:
            path = args[0]
        self.columnize([
            node['name'] for node in self.ctx.ls(path)
        ])
    
    @seaferr_protected
    def do_cd(self, path):
        """Go to path"""
        if path is None:
            path = '/'
        self.ctx.cd(path)
        self._update_prompt()
    
    @seaferr_protected
    def do_download(self, path):
        """Download a file"""
        self.ctx.download(path, os.path.join(os.path.expanduser('~'), filename))
    
    @seaferr_protected
    def do_upload(self, local):
        """Upload a local file to the cwd"""
        self.ctx.upload(local, self.ctx.cwd)
    
    def complete_upload(self, text, line, begidx, endidx):
        """Completion using the local filesystem"""
        # get the basepath for completion
        line = line[:begidx]
        if line.endswith('/'):
            # last part of line is part of basepath
            path = shlex.split(line)[-1]
            if path.startswith('/'):
                # absolute
                basepath = path
            else:
                # relative
                basepath = os.path.join(os.curdir, path)
        else:
            basepath = os.curdir
        basepath = os.path.expanduser(basepath)
        return [ 
            fname for fname in os.listdir(basepath) if fname.startswith(text)
        ]
    
    @seaferr_protected
    def do_rm(self, path):
        """Delete a file or a directory"""
        self.ctx.delete(path)
    
    @seaferr_protected
    def do_rmdir(self, path):
        """Delete a file or a directory"""
        self.ctx.delete(path)
    
    @seaferr_protected
    def do_addline(self, path):
        """Add a line in an textfile"""
        # tmp filename
        tmp = os.path.join(os.path.expanduser('~'), 'seafsh.tmp')
        # download path
        self.ctx.download(path, tmp)
        # open and add line
        with open(tmp, 'a') as f:
            f.write('newline\n')
        # udate file
        self.ctx.update(tmp, path)
        # delete tmp
        os.remove(tmp)
    
    @seaferr_protected
    def do_stat(self, path):
        """Print details about path"""
        print(self.ctx.stat(path))

    @seaferr_protected
    def do_printform(self, path):
        """Print the form content of a SeafForm"""
        formcli = SeafFormCli(self.ctx, path)
        formcli.print()
    
    @seaferr_protected
    def do_fillform(self, path):
        """Fill a SeafForm"""
        formcli = SeafFormCli(self.ctx, path)
        result = formcli.fill()
        print(result)
        formcli.post(result)
        
if __name__ == '__main__':
    
    conf_name = os.path.join(
        os.path.expanduser('~'),
        '.config/seafsh-knownhosts.json'
    )
    
    try:
        with open(conf_name, 'r') as conf:
            knownhosts = json.load(conf)
    except FileNotFoundError:
        print('You must create the file %s with known host configuration.')
        print('Sample:')
        print('''
[
    "host1": {
        "url": "https://example.com/",
        "email": "user@example.com",
        "password": "1234"
    },
    "host2": {
        "url": "https://example.org/seafile/",
        "email": "user@example.org",
        "token": "38516201a16a48ab9585b082e8cb49a6b3ec1234",
    }
’
''')
        print('After the first password authentication, you can remove your')
        print('password from this file and put the token instead.')
    else:
        ctx = SeafBrowser(knownhosts)    
        SeafileShell(ctx).cmdloop()
    

