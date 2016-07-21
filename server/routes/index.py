import flask
import json
import sbhstimetable.colours as colours

from flask import render_template, session
from flask.json import jsonify
from server import app
from server.dates import default_bells,getNextSchoolDay
from server.util import etagged


@app.route('/')
@etagged
def root():
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

@etagged
@app.route('/.well-known/assetlinks.json')
def app_link():
    return flask.send_from_directory('static', 'assetlinks.json')

