import flask

from flask import make_response
from flask.json import jsonify
from server import app
from server.routes.api import get_shs_api
from server.util import nocache

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