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

import time
import json
import os
import traceback
from calendar import MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY
from datetime import datetime, timedelta, date
from urllib.parse import quote_plus as urlencode

from flask import Flask, render_template, make_response, session
from flask.json import jsonify
from hashlib import sha1
from flask.sessions import session_json_serializer
from functools import wraps
import flask
import requests
import yaml
import re
from itsdangerous import URLSafeTimedSerializer
from dateutil.relativedelta import relativedelta
from scss.compiler import Compiler
from scss.namespace import Namespace
from scss.types import Color
import sbhstimetable.colours as colours

os.environ['TZ'] = 'Australia/Sydney' # force the right timezone

# from sessions import SqliteSessionInterface
app = Flask(__name__)

with open('config.yml') as c:
    cfg = yaml.load(c)

if not cfg['app']['debug'] and cfg['app']['sessionSecretKey'] == 'abcdefghijklmnop':
    raise Exception("Pls set proper sessionSecretKey before running in release mode")

app.secret_key = cfg['app']['sessionSecretKey']
app.config['SESSION_COOKIE_NAME'] = 'SESSID'  # for compat with that android app

### date/time helper functions
default_bells = {
    MONDAY: "[{'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},{'bell':'Lunch 1','time':'11:10'},{'bell':'Lunch 2','time':'11:30'},{'bell':'3','time':'11:50'},{'bell':'Transition','time':'12:50'},{'bell':'4','time':'12:55'},{'bell':'Recess','time':'13:55'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}]",
    WEDNESDAY: "[{'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},{'bell':'Recess','time':'11:10'},{'bell':'3','time':'11:30'},{'bell':'Lunch 1','time':'12:30'},{'bell':'Lunch 2','time':'12:50'},{'bell':'4','time':'13:10'},{'bell':'Transition','time':'14:10'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}]",
    FRIDAY: "[{'bell':'Roll Call','time':'09:25'},{'bell':'1','time':'09:30'},{'bell':'Transition','time':'10:25'},{'bell':'2','time':'10:30'},{'bell':'Recess','time':'11:25'},{'bell':'3','time':'11:45'},{'bell':'Lunch 1','time':'12:40'},{'bell':'Lunch 2','time':'13:00'},{'bell':'4','time':'13:20'},{'bell':'Transition','time':'14:15'},{'bell':'5','time':'14:20'},{'bell':'End of Day','time':'15:15'}]"
}

default_bells[TUESDAY] = default_bells[MONDAY]
default_bells[THURSDAY] = default_bells[WEDNESDAY]
default_bells['mon'] = default_bells['tue'] = [
    {'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},
    {'bell':'Lunch 1','time':'11:10'},{'bell':'Lunch 2','time':'11:30'},{'bell':'3','time':'11:50'},{'bell':'Transition','time':'12:50'},
    {'bell':'4','time':'12:55'},{'bell':'Recess','time':'13:55'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}
]
default_bells['thu'] = default_bells['wed'] = [
    {'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},
    {'bell':'Recess','time':'11:10'},{'bell':'3','time':'11:30'},{'bell':'Lunch 1','time':'12:30'},{'bell':'Lunch 2','time':'12:50'},
    {'bell':'4','time':'13:10'},{'bell':'Transition','time':'14:10'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}
]
default_bells['fri'] = [
    {'bell':'Roll Call','time':'09:25'},{'bell':'1','time':'09:30'},{'bell':'Transition','time':'10:25'},{'bell':'2','time':'10:30'},
    {'bell':'Recess','time':'11:25'},{'bell':'3','time':'11:45'},{'bell':'Lunch 1','time':'12:40'},{'bell':'Lunch 2','time':'13:00'},
    {'bell':'4','time':'13:20'},{'bell':'Transition','time':'14:15'},{'bell':'5','time':'14:20'},{'bell':'End of Day','time':'15:15'}
]


def getNextSchoolDay():
    now = datetime.now()
    if (now.hour < 15 or (now.hour == 15 and now.hour < 15)) and now.weekday() < SATURDAY:
        return now+relativedelta(hour=0,minute=0,second=0)
    elif now.weekday() >= FRIDAY:
        return now+relativedelta(hour=0,minute=0,second=0,weekday=MONDAY)
    else:
        return now+relativedelta(hour=0,minute=0,second=0,days=1)


def etagged(fn):
    get_hash = lambda s: 'W/"' + str(hash(s)) + "$" + str(len(s)) + '"'

    @wraps(fn)
    def tag():
        test = None
        if 'If-None-Match' in flask.request.headers:
            test = flask.request.headers['If-None-Match']
        orig_resp = fn()
        if type(orig_resp) == str:
            hash = get_hash(orig_resp)
            if hash == test:
                print("NOT MODIFIED")
                res = make_response()
                res.status = 'Not Modified'
                res.status_code = 304
                return res
            res = make_response(orig_resp)
            res.headers['ETag'] = hash
            return res
        elif orig_resp is not None:
            o = orig_resp.get_data(as_text=True)
            hash = get_hash(o)
            if hash == test:
                res = make_response()
                res.status = 'Not Modified'
                res.status_code = 304
                return res
            orig_resp.headers['ETag'] = hash
            return orig_resp
        print("None response from etagged function!")
        flask.abort(404)
    return tag

def nocache(fn):
    @wraps(fn)
    def uncache(*args, **kwargs):
        orig_resp = fn(*args, **kwargs)
        if type(orig_resp) == Flask.response_class:
            print("RESPONSE CLASS")
        else:
            orig_resp = make_response(orig_resp)
        orig_resp.headers['Prgama'] = 'no-cache'
        orig_resp.headers['Expires'] = 'Sat, 26 Jul 1997 05:00:00 GMT'
        orig_resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return orig_resp
    return uncache


@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=90)


# routes
@app.route('/')
@etagged
def root():
    print(getNextSchoolDay())
    userData = {}
    if 'access_token' in session:
        if 'user_data' not in session or 'error' in session['user_data']:
            session['user_data'] = get_shs_api('details/userinfo.json')
        if 'error' not in session['user_data']:
            userData['year'] = session['user_data']['yearGroup']
            userData['fname'] = session['user_data']['givenName']
            userData['lname'] = session['user_data']['surname']
    config = {
        'bells': {'bells': json.loads(default_bells[getNextSchoolDay().weekday()].replace("'", '"'))},
        'nextHolidayEvent': app.next_event.timestamp() * 1000,
        'holidayEventData': app.next_event_data,
        'loggedIn': 1 if ('access_token' in session) else 0,
        'holidayCfg': {
            'video': 'Sagg08DrO5U',
            'videoURIQuery': '',
            'text': 'doot doot',
            'background': '/static/icon.png'
        },
        'userData': userData,
        'HOLIDAYS': int(not app.inTerm)
    }
    scheme = ''
    if 'colour' in flask.request.args:
        scheme = colours.get(flask.request.args['colour'], 'invert' in flask.request.args)
    elif 'invert' in flask.request.args:
        scheme = colours.get('default', True)
    else:
        scheme = colours.get('default', False)
    config['cscheme'] = scheme.asdict()
    return render_template('index.html', jsonify=jsonify, config=config, scheme=scheme)


@app.route('/api/today.json')
@nocache
def today():
    #return 'Yep - ' + str(getNextSchoolDay())
    json = get_shs_api('timetable/daytimetable.json', flask.request.args)
    if json['httpStatus'] != 200:
        r = make_response(jsonify(json))
        r.status_code = json['httpStatus']
        return r
    prettified = {
        'httpStatus': 200,
        '_fetchTime': json['_fetchTime'],
        'date': json['date']
    }
    version = flask.request.args['v'] if 'v' in flask.request.args else 1
    if version == 1:
        prettified['variationsFinalised'] = json['shouldDisplayVariations']
    else:
        prettified['displayVariations'] = json['shouldDisplayVariations']
    # merge room and class variations into one object
    variations = {}
    if len(json['classVariations']) > 0:
        t = json['classVariations']
        for k in t:
            subj = t[k]['year'] + t[k]['title'] + '_' + t[k]['period']
            if 'casualSurname' not in t[k]:
                t[k]['casualSurname'] = None
            variations[subj] = {
                'hasCover': t[k]['type'] != 'nocover',
                'casual': t[k]['casual'],
                'casualDisplay': t[k]['casualSurname'],
                'cancelled': t[k]['type'] == 'nocover',
                'hasCasual': t[k]['type'] == 'replacement',
                'varies': t[k]['type'] != 'novariation'
            }
            if version > 1:
                variations[subj]['teacherVaries'] = variations[subj]['varies']
    if len(json['roomVariations']) > 0:
        t = json['roomVariations']
        for k in t:
            subj = t[k]['year'] + t[k]['title'] + '_' + t[k]['period']
            if subj not in variations:
                variations[subj] = {}
            variations[subj]['roomFrom'] = t[k]['roomFrom']
            variations[subj]['roomTo'] = t[k]['roomTo']

    # and bells - only period bells
    bells = {}
    for i in range(len(json['bells'])):
        if json['bells'][i]['bell'] is not None and json['bells'][i]['bell'][0].isdigit():
            b = {
                'start': json['bells'][i]['time'],
                'title': json['bells'][i]['bellDisplay'],
                'end': json['bells'][i+1]['time'],
                'next': json['bells'][i+1]['bellDisplay']
            }
            bells[json['bells'][i]['bell']] = b
    prettified['today'] = json['timetable']['timetable']['dayname']

    temp = prettified['today'].split()
    dayNumber = 'Monday Tuesday Wednesday Thursday Friday'.split().index(temp[0])
    dayNumber += 5 * 'A B C'.split().index(temp[1])
    prettified['dayNumber'] = dayNumber
    prettified['weekType'] = temp[1]

    prettified['timetable'] = json['timetable']['timetable']['periods']
    if 'R' in prettified['timetable']: del prettified['timetable']['R']
    prettified['hasVariations'] = len(variations) > 0

    for i in prettified['timetable']:
        temp = prettified['timetable'][i]
        subjID = temp['year'] + temp['title'] # 10MaA
        if subjID in json['timetable']['subjects']:
            subjInfo = json['timetable']['subjects'][subjID]
        else:
            # an accelerant? try the next year.
            _subjID = str(int(temp['year']) + 1) + temp['title']
            if _subjID in json['timetable']['subjects']:
                subjInfo = json['timetable']['subjects'][_subjID]
            else:
                subjInfo = {'title': 'a b'}
        # subjInfo['title'] is of the form "10 Maths A"
        title = re.sub(r' [A-Z0-9]$', '', subjInfo['title']).split() # remove the A/1 - ['10', 'Maths']
        prettified['timetable'][i]['fullName'] = ' '.join(title[1:]) # 'Maths'
        prettified['timetable'][i]['fullTeacher'] = re.sub(r' . ', ' ', subjInfo['fullTeacher']) # remove initial

        prettified['timetable'][i]['bell'] = bells[i]
        subjID += '_' + i
        prettified['timetable'][i]['changed'] = False
        if subjID in variations:
            prettified['timetable'][i]['changed'] = True
            for j in variations[subjID]:
                prettified['timetable'][i][j] = variations[subjID][j]
    return jsonify(prettified)


@app.route('/api/notices.json')
@nocache
def notices():
    obj = get_shs_api('dailynews/list.json', flask.request.args)
    if obj['httpStatus'] != 200:
        r = make_response(jsonify(obj))
        r.status_code = obj['httpStatus']
        return r
    prettified = {
        'httpStatus': 200,
        '_fetchTime': int(time.time())
    }
    weighted = {}

    if obj['dayInfo']:
        prettified['date'] = obj['dayInfo']['date']
        prettified['term'] = obj['dayInfo']['term']
        prettified['week'] = obj['dayInfo']['week'] + obj['dayInfo']['weekType']
    else:
        prettified['date'] = prettified['week'] = prettified['term'] = None

    for i in range(len(obj['notices'])):
        pEntry = {'isMeeting': False}
        weight = 0
        entry = obj['notices'][i]
        weight = int(entry['relativeWeight'])
        entry['isMeeting'] = entry['isMeeting'] == '1'
        if entry['isMeeting']:
            weight += 1
            pEntry['isMeeting'] = True
            pEntry['meetingDate'] = entry['meetingDate']
            if entry['meetingTimeParsed'] != '00:00:00':
                pEntry['meetingTime'] = entry['meetingTimeParsed']
            else:
                pEntry['meetingTime'] = entry['meetingTime']
            pEntry['meetingPlace'] = entry['meetingLocation']
        pEntry['id'] = entry['id']
        pEntry['dTarget'] = entry['displayYears']
        pEntry['years'] = entry['years']
        pEntry['title'] = entry['title']
        pEntry['text'] = entry['content']
        pEntry['author'] = entry['authorName']
        pEntry['weight'] = weight
        if weight in weighted:
            weighted[weight].append(pEntry)
        else:
            weighted[weight] = [pEntry]

    prettified['notices'] = weighted
    return jsonify(prettified)


@app.route('/logout')
def logout():
    to_del = list(session.keys())
    for key in to_del:
        del session[key]
    return flask.redirect('/')


@app.route('/api/bettertimetable.json')
@nocache
def btimetable():
    obj = get_shs_api('timetable/timetable.json', flask.request.args)
    if obj['httpStatus'] != 200:
        r = make_response(jsonify(obj))
        r.status_code = obj['httpStatus']
        return r
    prettified = {
        'httpStatus': 200,
        '_fetchTime': obj['_fetchTime'],
        'days': obj['days'],
        'subjInfo': {}
    }
    for i in obj['subjects']:
        b = obj['subjects'][i]
        if type(b) != dict: continue
        if not b['title']: continue
        b['title'] = b['title'].split()
        if len(b['title'][-1]) == 1:
            b['title'] = b['title'][1:-1]
        else:
            b['title'] = b['title'][1:]
        b['title'] = ' '.join(b['title'])
        prettified['subjInfo'][b['year'] + '' + b['shortTitle']] = b
    return jsonify(prettified)


@app.route('/api/belltimes')
@nocache
def bells():
    obj = get_shs_api('timetable/bells.json', flask.request.args)
    if obj['httpStatus'] != 200 or obj['status'] == 'Error':
        r = make_response(jsonify(obj))
        r.status_code = obj['httpStatus']
        return r
    shortDow = obj['day'].lower()[:3]
    normal = default_bells[shortDow]
    for i in range(len(obj['bells'])):
        obj['bells'][i]['index'] = i
        if normal[i]['time'] != obj['bells'][i]['time']:
            obj['bells'][i]['different'] = True
            obj['bells'][i]['normally'] = normal[i]['time']
    return jsonify(obj)

@app.route('/try_do_oauth')
def begin_oauth():
    if 'access_token' in session:
        return flask.redirect('/?loggedIn=true&mobile_loading')
    return flask.redirect(
        'https://student.sbhs.net.au/api/authorize?response_type=code&client_id=' + cfg['app']['clientID']
        + '&redirect_uri=' + urlencode(cfg['app']['redirectURI'])
        + '&scope=all-ro&state=' + str(int(time.time())))

@app.route('/login')
def handle_login_callback():
    qs = flask.request.args
    payload = {
        'grant_type': 'authorization_code',
        'redirect_uri': cfg['app']['redirectURI'],
        'code': qs['code'],
        'client_id': cfg['app']['clientID'],
        'client_secret': cfg['app']['secret'],
        'state': qs['state']
    }
    try:
        r = requests.post('https://student.sbhs.net.au/api/token', payload)
        obj = r.json()
        session['access_token'] = obj['access_token']
        session['refresh_token'] = obj['refresh_token']
        session['expires'] = int(time.time()) + obj['expires_in']
        session['user_data'] = get_shs_api('details/userinfo.json')
    except Exception as e:
        print("Error reaching SBHS!", e)
    return flask.redirect('/?loggedIn=true&mobile_loading=true')

def refresh_api_token(session=session):
    if 'expires' not in session: # not logged in
        return False
    if time.time() > session['expires']:
        refreshToken = session['refresh_token']
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refreshToken,
            'client_id': cfg['app']['clientID'],
            'redirect_uri': cfg['app']['redirectURI'],
            'client_secret': cfg['app']['secret']
        }
        try:
            r = requests.post('https://student.sbhs.net.au/api/token', payload)
            obj = r.json()
            session['access_token'] = obj['access_token']
            session['expires'] += 3600
        except Exception as e:
            print("Error reaching SBHS!", e)
            return False
        return True
    return True

def manually_deserialize_session(val):
    s = URLSafeTimedSerializer(cfg['app']['sessionSecretKey'], salt='cookie-session',
                               serializer=session_json_serializer,
                               signer_kwargs={'key_derivation': 'hmac', 'digest_method': sha1})
    try:
        session_data = s.loads(val)
    except Exception as e:
        print("Failed to load session from querystring!", e)
        traceback.print_tb(e.__traceback__)
        session_data = {}
    return session_data

def get_shs_api(path, qs=None):
    r = None
    try:
        if qs is None:
            qs = dict()
        else:
            qs = dict(qs) # mutable yay
        if flask.request:
            if 'SESSID' in qs: # mobile app compatibility
                if qs['SESSID'][0] != 'undefined':
                    sdata = manually_deserialize_session(qs['SESSID'][0])
                    refresh_api_token(sdata)
                    if 'access_token' in sdata: qs['access_token'] = sdata['access_token']
                del qs['SESSID']
            else:
                refresh_api_token()
                if 'access_token' in session: qs['access_token'] = session['access_token']
        r = requests.get('https://student.sbhs.net.au/api/' + path, params=qs)
        if r.status_code == 200:
            now = int(time.time())
            obj = r.json()
            obj['httpStatus'] = 200
            obj['_fetchTime'] = now
            return obj
        else:
            return {'error': 'invalid sbhs code', 'httpStatus': r.status_code, '_fetchTime': int(time.time())}
    except Exception as e:
        status = 500
        if r:
            # probably an invalid API option
            print("Error reaching SBHS! (got", r.text, ")",  e)
            status = r.status_code if r.status_code != 200 else 404
        else:
            print("Error reaching SBHS!", e)
        traceback.print_tb(e.__traceback__)
        return {'error': 'connection failed', 'httpStatus': status, '_fetchTime': int(time.time())}

@app.route('/api/<path:api>')
@nocache
def api(api):
    obj = get_shs_api(api, flask.request.args)
    r = make_response(jsonify(obj))
    r.status_code = (obj['httpStatus'] if 'httpStatus' in obj else 500)
    return r

def find_next_event(app):
    terms = app.terms
    for i in ['1', '2', '3', '4']:
        (year, month, day) = map(int, terms[i]['start']['date'].split('-'))
        dt = datetime(year, month=month, day=day, hour=9, minute=5)
        if dt > datetime.now():
            app.next_event = dt
            app.inTerm = False
            app.next_event_data = {
                'term': i,
                'end': 0
            }
            break
        (year, month, day) = map(int, terms[i]['end']['date'].split('-'))
        dt = datetime(year, month=month, day=day, hour=15, minute=15)
        if dt > datetime.now():
            app.next_event = dt
            app.next_event_data = {
                'term': i,
                'end': 1
            }
            app.inTerm = True
            break

@etagged
@app.route('/.well-known/assetlinks.json')
def app_link():
    return flask.send_from_directory('static', 'assetlinks.json')

@etagged
@app.route('/style/index.css')
def customise_css():
    colour = colours.get_from_qs(flask.request.args)
    namespace = Namespace()
    namespace.set_variable('$fg', Color.from_hex(colour.fg))
    namespace.set_variable('$bg', Color.from_hex(colour.bg))
    namespace.set_variable('$highFg', Color.from_hex(colour.highFg))
    namespace.set_variable('$highBg', Color.from_hex(colour.highBg))

    compiler = Compiler(namespace=namespace)
    res = make_response(compiler.compile('style/index.scss'))
    res.mimetype = 'text/css'
    return res

@app.before_request
def check_time():
    if datetime.now() > app.next_event:
        find_next_event(app)


if __name__ == '__main__':
    if cfg['app']['debug']:
        print("Generating new belltimes.concat.js...")
        from sbhstimetable.jsconcat import concat_js
        concat_js('script')
        print("Done!")
    else:
        from os import path
        if not path.exists('static/belltimes.concat.js'.replace('/', path.sep)):
            raise Exception("Belltimes.concat.js does not exist, pls create - python -m sbhstimetable.jsconcat")
    print("Loading term data...")
    res = get_shs_api("calendar/terms.json", qs={'year': date.today().year})
    if 'error' in res:
        raise Exception("rip")
    terms = res['terms']
    app.terms = terms
    app.next_event = 0
    app.inTerm = True
    find_next_event(app)
    print("Done")

    app.run(debug=cfg['app']['debug'], threaded=True, port=cfg['net']['port'], host='0.0.0.0')
