# -*- coding: utf-8 -*-
###############################################################################
#       seafform/seafile.py
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
"""Seafile API wrapper"""

__author__ = "Florian Birée"
__version__ = "0.2"
__license__ = "AGPLv3"
__copyright__ = "Copyright © 2015, Florian Birée <florian@biree.name>"

import os
from functools import wraps
from urllib.parse import urljoin, urlparse
import requests
from requests.exceptions import HTTPError
import json

# HTTP verbs
GET = requests.get
POST = requests.post
PUT = requests.put
DELETE = requests.delete

# Seafile exceptions
class SeafileError(Exception):
    """Base class for all Seafile-related exceptions"""

class NotAuthenticated(SeafileError):
    """Raised when trying an operation that need authentication"""
    pass

class AuthError(SeafileError):
    """Authentification error"""
    pass

class APIError(SeafileError):
    """API error"""
    msg = "Seafile API error"
    def __init__(self, curl_cmd=None, msg=None):
        """APIError(curl_cmd, *args)"""
        self.curl_cmd = curl_cmd
        if msg:
            self.msg = msg
    
    def __add__curl(self, msg):
        if self.curl_cmd:
            return msg + '\n$ ' + self.curl_cmd
        else:
            return msg
    
    def __str__(self):
        return self.__add__curl(self.msg)

class BadPath(APIError):
    code = 400
    msg = "400 Path is missing/bad."

class Forbidden(APIError):
    code = 403
    msg = "403 Forbidden"

class NotFound(APIError):
    code = 404
    msg = "404 The path does not exists."

class InvalidPath(APIError):
    code = 440
    msg = "440 Invalid path or filname, or encrypted repo."

class FileExists(APIError):
    code = 441
    msg = "441 File already exists."

class InternalServerError(APIError):
    code = 500
    msg = "500 Internal server error (may be out of quota)."

class OperationFailed(APIError):
    code = 520
    msg = "520 Operation failed."

EXCEPT_CODE = {
    '400': BadPath,
    '403': Forbidden,
    '404': NotFound,
    '440': InvalidPath,
    '441': FileExists,
    '500': InternalServerError,
    '520': OperationFailed,
}

def curlify(request):
    """Return a curl command line corresponding to the `request`"""
    return (
        'curl -v ' +
        ('-X PUT ' if request.method == 'PUT' else '') +
        (('-d "%s" ' % request.body) if request.body else '') +
        ' '.join("-H '%s: %s'" % (k, v) for (k, v) in request.headers.items()) +
        ' ' +
        request.url
    )

class Seafile:
    """Seafile connector"""
    
    base_api = 'api2/'
    
    # internals
    
    def __init__(self, url, verifycerts=True):
        """New seafile connector to `url` instance
        
            set verifycerts to False to disable TLS certificate verification
        """
        self.url = url
        self._api_url = urljoin(self.url, self.base_api)
        self.token = None
        self.email = None
        self.verify = verifycerts
    
    def _need_auth(func):
        """Decorator to ensure the connector is authentified before 
        executing `func`"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.token is None:
                raise NotAuthenticated
            return func(self, *args, **kwargs)
        return wrapper
    
    def __repr__(self):
        """String representation of the object"""
        hostname = urlparse(self.url).hostname
        if self.token is None:
            return "<Seafile({hostname})>".format({'hostname': hostname})
        else:
            return "<Seafile({email}@{hostname})>".format({
                'email': self.email,
                'hostname': hostname
            })
    
    def _api(self, verb, cmd, params=None, data=None, headers=None, files=None,
                   token=True, raw_url=False):
        """Execute the API command VERB `cmd`
        
            VERB is one of GET, POST, PUT, DELETE
        
            `params` : optionals ?= params
            `headers` : optionals headers
            `data` : optionals POST or PUT data
            `files` : POST data content using the Content-Type                  
                multipart/form-data (RFC 2388). If a value in the data dict is   
                an opened file object, it will be sent as a file.
            
            if `token`, add the Authorization header
            if `raw_url`, use `cmd` as full url instead of concatenating `cmd`
                to the API url.
            
            Return json-loaded data
        """
        final_headers = {'Accept': 'application/json; indent=4; charset=utf-8'}
        if headers:
            final_headers.update(headers)
        if token:
            final_headers['Authorization'] = 'Token ' + self.token
        
        r = verb(
            urljoin(self._api_url, cmd) if not raw_url else cmd,
            params=params,
            headers=final_headers,
            data=data,
            files=files,
            verify=self.verify
        )
        try:
            r.raise_for_status()
        except HTTPError:
            apierror = EXCEPT_CODE.get(r.status_code, APIError)
            raise apierror(
                curlify(r.request),
                r.text
            )
        else:
            return r.json()
    
    def _multipart_filname_patching(self, prepped, filename):
        """Since Seafile doesn't handle well RFC2231
            wich specify to send filename*= field for utf-8 characters
            (which is what Requests does), we patch the request body
            to put just a raw utf-8 filename (like curl does)
        
            this is a dirty hack
            
            `prepped` is a prepared request
            `filename` is the str filename to encode in raw utf-8
            
            return the patched prepped
        """
        starbytes = b'filename*='
        # find the start of starbytes
        start = prepped.body.find(starbytes)
        if start == -1:
            # not here, return prepped unchanged
            return prepped
        # find the first \r\n sequence after starbytes (end of filename)
        end = prepped.body.find(b'\r\n', start)
        
        # patch the body
        prepped.body = (
            prepped.body[:start] +
            b'filename="' + filename.encode('utf8') + b'"' +
            prepped.body[end:]
        )
        # recompute the Content-Length header
        prepped.headers['Content-Length'] = str(len(prepped.body))
        return prepped

    # auth methods
    
    def authenticate(self, email, password=None, token=None, validate=True):
        """Authenticate against the Seafile server, with `email` and either:
            - `password` : to authenticate with a password
            - `token` : to reuse a token from a previous authentication
            
            if success, the token is available at self.token
            else raise AuthError
            
            if not validate, the Seafile connector will not check the validy of
                the token (if token authentication).
                No seafile request will be done. If you are sure about your
                token validy, this will save time.
        """
        if password is None and token is None:
            raise ValueError
        elif token is not None: # token auth
            if validate:
                # try to validate the token
                try:
                    self._auth_ping(token)
                except SeafileError:
                    raise AuthError
                else:
                    self.token = token
                    self.email = email
            else:
                self.token = token
                self.email = email
        else: # password auth
            try:
                resp = self._api(POST, 'auth-token/', data={
                    'username': email,
                    'password': password
                }, token=False)
            except:
                raise AuthError
            else:
                if resp['token']:
                    self.token = resp['token']
                    self.email = email
    
    # test methods
    
    def ping(self):
        """Ping the Seafile server
        
            raise SeafileError if not working
        """
        if not self._api(GET, 'ping/', token=False) == "pong":
            raise SeafileError
        
    def _auth_ping(self, token):
        """Ping the Seafile server with the token `token`
        
            raise SeafileError if not working
        """
        # here the token may not be validated, so we do not use _api(token=True)
        headers = {'Authorization': 'Token ' + token}
        resp = self._api(GET, 'auth/ping/', headers=headers, token=False)
        if resp != "pong":
            raise SeafileError
        
    @_need_auth
    def auth_ping(self):
        """Ping the Seafile server with the token `token`
        
            raise SeafileError if not working
        """
        self._auth_ping(self.token)
    
    # library methods
    
    @_need_auth
    def list_repos(self):
        """List repos/librarys
            
            return a list of {
                "permission": "rw",
                "encrypted": false,
                "mtime": 1400054900,
                "owner": "user@mail.com",
                "id": "f158d1dd-cc19-412c-b143-2ac83f352290",
                "size": 0,
                "name": "foo",
                "type": "repo",
                "virtual": false,
                "desc": "new library",
                "root": "0000000000000000000000000000000000000000"
            }
        """
        return self._api(GET, 'repos/')

    # directory methods

    @_need_auth
    def list_dir(self, repo_id, path="/"):
        """list the content of a directory from library `repo_id`/`path`
        
            return a list of {
                "id": "e4fe14c8cda2206bb9606907cf4fca6b30221cf9",
                "type": "file|dir",
                "name": "test",
                "size": 0, # only for files
            }
            
            Errors:
                404 NotFound
                440 InvalidPath (encrypted repo)
                520 OperationFailed
        """
        return self._api(
            GET,
            'repos/{repo_id}/dir/'.format(repo_id=repo_id),
            {'p': path}
        )
        
    # files methods
    
    @_need_auth
    def open_file(self, repo_id, path):
        """get the file `repo_id`/`path`.
        
            Return an opened requests.Response.raw file-like object
            
            Errors:
                400 BadPath
                404 NotFound 
                520 OperationFailed
        """
        # get the file link
        flink = self._api(
            GET,
            'repos/{repo_id}/file/'.format(repo_id=repo_id),
            {'p': path}
        )
        resp = requests.get(flink, stream=True)
        resp.raw.decode_content = True
        return resp.raw
    
    @_need_auth
    def lock_file(self, repo_id, path):
        """lock the file `repo_id`/`path`.
        
            Not implemented server side.
        """
        raise NotImplementedError
        #return (self._api_cmd(
        #    'repos/{repo_id}/file/'.format(repo_id=repo_id),
        #    {'operation': 'lock', 'p': path},
        #    put=True
        #) == "success")
    
    @_need_auth
    def unlock_file(self, repo_id, path):
        """unlock the file `repo_id`/`path`.
        
            Not implemented server side.
        """
        raise NotImplementedError
        #return (self._api_cmd(
        #    'repos/{repo_id}/file/'.format(repo_id=repo_id),
        #    {'operation': 'unlock', 'p': path},
        #    put=True
        #) == "success")
    
    @_need_auth
    def upload_file(self, repo_id, parent, fileo):
        """upload the file object `fileo` to `repo_id`/`parent`
        
            Return the file id
            
            Errors:
                400 BadPath
                440 InvalidPath
                441 FileExists
                500 InternalServerError (out of quota)
        """
        # get upload link
        up_link = self._api(GET,
            'repos/{repo_id}/upload-link/'.format(repo_id=repo_id)
        )
        
        filename = os.path.split(fileo.name)[1]
        # upload file
        s = requests.Session()
        req = requests.Request('POST',
            up_link,
            files={
                'filename': (None, filename),
                'parent_dir': (None, parent),
                'file': (filename, fileo, 'application/octet-stream'),
            },
            verify=self.verify
        )
        prepped = self._multipart_filname_patching(req.prepare(), filename)
        
        r = s.send(prepped, stream=False)
        try:
            r.raise_for_status()
        except HTTPError:
            apierror = EXCEPT_CODE.get(r.status_code, APIError)
            raise apierror(
                curlify(r.request),
                r.text
            )
        else:
            return r.text
    
    @_need_auth
    def update_file(self, repo_id, filepath, fileo):
        """update the file `repo_id`/`filepathe` with the file object `fileo`
        
            Return the file id
            
            Errors:
                400 BadPath
                440 InvalidPath
                500 InternalServerError (out of quota)
        """
        # get update link
        up_link = self._api(GET,
            'repos/{repo_id}/update-link/'.format(repo_id=repo_id)
        )
        
        filename = os.path.split(fileo.name)[1]
        # upload file
        s = requests.Session()
        req = requests.Request('POST',
            up_link,
            files={
                #'filename': (None, filename),
                'target_file': (None, filepath),
                'file': (filename, fileo, 'application/octet-stream'),
            },
            verify=self.verify,
        )
        prepped = self._multipart_filname_patching(req.prepare(), filename)
        
        r = s.send(prepped, stream=False)
        try:
            r.raise_for_status()
        except HTTPError:
            apierror = EXCEPT_CODE.get(r.status_code, APIError)
            raise apierror(
                curlify(r.request),
                r.text
            )
        else:
            return r.text
    
    
    @_need_auth
    def delete_file(self, repo_id, path):
        """delete the file or directory `repo_id`/`path`
        
            Errors:
                400 BadPath
                520 OperationFailed
        """
        return (self._api(DELETE,
            'repos/{repo_id}/file/'.format(repo_id=repo_id),
            params={'p': path}
        ) == "success")

    @_need_auth
    def stat_file(self, repo_id, path):
        """get data about the file `repo_id`/`path`
        
            Return {'id', 'mtime', 'type':'file', 'name', 'size'}
            
            Errors:
                400 BadPath
                520 OperationFailed
        """
        return self._api(GET,
            'repos/{repo_id}/file/detail/'.format(repo_id=repo_id),
            params={'p': path}
        )


