# Seafile forms - installation instructions

## Requierments

- Python 3
- Python virtual environments
- Django 1.10
- Python3-lxml
- Python3-requests
- Python3-ezodf (not in Debian packages)
- Python3-bootstrapform

You really should install SeafForm under HTTPS, since personnal informations
will be transfered in the network

## Where you should install SeafForm?

SeafForm use the same credentials than the Seafile server. To avoid leaking
username and passwords of Seafile users, you should only install SeafForm either:

- on a server administrated by the same people than the Seafile one (you
  trust the same people)
- on your personnal server for you own use (if you can trust yourself)

## How to install it?

### Get the code
*put it in a directory not in your server document root, lets says:*

    $ cd /var/webapps/
    $ git clone https://github.com/flobiree/seafform.git

### Dependencies
*here are the Debian/Stretch packages, if needed libs are not packaged in
you distribution, install them using pip at the next step*

    # apt-get install python3 python3-virtualenv python3-django python3-bootstrapform python3-lxml python3-requests virtualenv

### Initialize the virtual environment and dependencies

    $ virtualenv --python=python3 --system-site-packages venv/
    $ cd venv/ # go to the virtual env to install python packages
    $ . bin/activate
    $ pip install ezodf gunicorn

## Create a Seafile library for forms templates

Get the content of the _forms-library_ directory, and put it inside a Seafile library. Get a share link for this library.

## Configuring the app

In venv/seafformsite/seafformsite/ copy settings.py.sample to settings.py, and
change it for your needs (read the whole file to find settings you need to change).
There is a setting to put your template share link.

*You must read the Django checklist to configure SeafForms for production!*
https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

You must initialize you database using:
    
    $ cd seafformsite
    $ ./manage.py migrate

### Starting the app
*You can use Gunicorn to run SeafForms, and start it with a process manager like supervisord*

The _seafform.sh_ script is here to start Gunicorn the right way. Edit it to at
last set the VENV_DIR variable.

See doc/seafform-supervisor.conf for a supervisord configuration snippet.

### Configure your webserver

Tell your webserver (Apache, Nginx) to communicate to the SeafForm socket. And be sure you use only HTTPS (with HSTS if possible).

See doc/seafform-nginx for an nginx configuration snippet.

## Test!

It should works!
