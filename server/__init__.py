# sbhs-timetable-python
# Copyright (C) 2015 Simon Shields, James Ye
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import yaml
from flask import Flask

app = Flask(__name__)

with open('config.yml') as c:
    cfg = yaml.load(c)

if not cfg['app']['debug'] and cfg['app']['sessionSecretKey'] == 'abcdefghijklmnop':
    raise Exception("Pls set proper sessionSecretKey before running in release mode")

app.secret_key = cfg['app']['sessionSecretKey']
app.config['SESSION_COOKIE_NAME'] = 'SESSID'  # for compat with that android app



