import flask
import re

from server import app
from server.routes.api import get_shs_api
from server.util import nocache
from flask.json import jsonify

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
