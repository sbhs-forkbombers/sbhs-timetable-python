import flask
import requests
import time

from flask import session
from server import app, cfg

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

@app.route('/logout')
def logout():
    to_del = list(session.keys())
    for key in to_del:
        del session[key]
    return flask.redirect('/')
