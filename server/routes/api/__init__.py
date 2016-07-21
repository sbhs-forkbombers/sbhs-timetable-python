import flask
import requests
import time
import traceback

from flask import make_response, session
from flask.json import jsonify
from server import app
from server.routes.login import refresh_api_token
from server.util import manually_deserialize_session, nocache

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

# import custom api routes
import server.routes.api.belltimes
import server.routes.api.notices
import server.routes.api.timetable
import server.routes.api.today

@app.route('/api/<path:api>')
@nocache
def api(api):
    obj = get_shs_api(api, flask.request.args)
    r = make_response(jsonify(obj))
    r.status_code = (obj['httpStatus'] if 'httpStatus' in obj else 500)
    return r
