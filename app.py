
import os
import yaml

from datetime import date
from server import app
from server.routes.api import get_shs_api
from server.dates import find_next_event

import server.routes # will import all routes

os.environ['TZ'] = 'Australia/Sydney' # force the right timezone

with open('config.yml') as c:
    cfg = yaml.load(c)

if not cfg['app']['debug'] and cfg['app']['sessionSecretKey'] == 'abcdefghijklmnop':
    raise Exception("Pls set proper sessionSecretKey before running in release mode")

if __name__ == '__main__':
    if cfg['app']['debug']:
        print("Generating new belltimes.concat.js...")
        from sbhstimetable.jsconcat import concat_js
        concat_js('script')
        print("Done!")
    else:
        from os import path
        if not path.exists('server/static/belltimes.concat.js'.replace('/', path.sep)):
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