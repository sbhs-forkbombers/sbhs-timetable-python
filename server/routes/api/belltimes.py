import flask

from flask import make_response
from flask.json import jsonify
from server import app
from server.dates import default_bells
from server.util import nocache
from server.routes.api import get_shs_api

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
