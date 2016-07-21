import flask
import time

from flask import make_response
from flask.json import jsonify
from server import app
from server.routes.api import get_shs_api
from server.util import nocache

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