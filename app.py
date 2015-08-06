from flask import Flask, render_template, make_response, g, session
from flask.json import jsonify
import time
import flask
import requests
import yaml
import json
from calendar import MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY
from datetime import datetime
from dateutil.relativedelta import MO, TU, WE, TH, FR, SA, SU, relativedelta
from urllib.parse import quote_plus as urlencode
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

def getNextSchoolDay():
    now = datetime.now()
    if now.hour < 15 or (now.hour == 15 and now.hour < 15) and now.weekday() < SATURDAY:
        return now+relativedelta(hour=0,minute=0,second=0)
    elif now.weekday() >= SATURDAY:
        return now+relativedelta(hour=0,minute=0,second=0,weekday=MONDAY)
    else:
        return now+relativedelta(hour=0,minute=0,second=0,days=1)

### routes
@app.route('/')
def root():
    config = {
        'bells': {'bells': json.loads(default_bells[getNextSchoolDay().weekday()].replace("'", '"')) },
        'nextHolidayEvent': app.next_event.timestamp() * 1000
    }
    return render_template('index.html', jsonify=jsonify, config=config)


@app.route('/api/today.json')
def today():
    return 'Yep - ' + str(getNextSchoolDay())

@app.route('/api/belltimes')
def bells():
    return get_shs_api('timetable/bells.json', flask.request.args)

@app.route('/try_do_oauth')
def begin_oauth():
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
    except Exception as e:
        print("Error reaching SBHS!", e)
    return flask.redirect('/')


def refresh_api_token():
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


def get_shs_api(path, qs=None):
    try:
        if flask.request: refresh_api_token()
        r = requests.get('https://student.sbhs.net.au/api/' + path, params=qs)
        if r.status_code == 200:
            now = int(time.time())
            obj = r.json()
            obj['_fetchTime'] = now
            return obj
        else:
            return {'error': 'invalid sbhs code', 'httpStatus': r.status_code, '_fetchTime': int(time.time())}
    except Exception as e:
        print("Error reaching SBHS!", e)
        return {'error': 'connection failed', 'httpStatus': 500, '_fetchTime': int(time.time())}


@app.route('/api/<path:api>')
def api(api):
    return jsonify(get_shs_api(api, flask.request.args))


if __name__ == '__main__':

    print("Loading term data...")
    res = get_shs_api("calendar/terms.json")
    if 'error' in res:
        raise Exception("rip")
    terms = res['terms']
    app.terms = terms
    print("Done")
    for i in ['1', '2', '3', '4']:
        (year, month, day) = map(int, terms[i]['start']['date'].split('-'))
        dt = datetime(year, month=month, day=day, hour=9, minute=5)
        if dt > datetime.now():
            app.next_event = dt
            break
        (year, month, day) = map(int, terms[i]['end']['date'].split('-'))
        dt = datetime(year, month=month, day=day, hour=15, minute=15)
        if dt > datetime.now():
            app.next_event = dt
            break
    app.run(debug=cfg['app']['debug'], threaded=True, port=cfg['net']['port'])
