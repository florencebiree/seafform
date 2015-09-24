#!/bin/bash
###############################################################################
#       seafform.sh
#       Gunicorn starting script
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

# change those variables to suits your needs
VENV_DIR=/path/to/seafform/venv/
ACTIVATE_PATH=$VENV_DIR/bin/activate
SOCKET="unix:/$VENV_DIR/seafform.sock"


cd ${VENV_DIR}
source ${ACTIVATE_PATH}
cd seafformsite
exec gunicorn --bind="$SOCKET" seafformsite.wsgi
