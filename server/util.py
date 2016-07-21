import flask
import traceback

from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, make_response, session
from itsdangerous import URLSafeTimedSerializer
from server import app
from server.dates import find_next_event

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
        flask.abort(404)
    return tag

def nocache(fn):
    @wraps(fn)
    def uncache(*args, **kwargs):
        orig_resp = fn(*args, **kwargs)
        if type(orig_resp) != Flask.response_class:
            orig_resp = make_response(orig_resp)
        orig_resp.headers['Prgama'] = 'no-cache'
        orig_resp.headers['Expires'] = 'Sat, 26 Jul 1997 05:00:00 GMT'
        orig_resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return orig_resp
    return uncache

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

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=90)


@app.before_request
def check_time():
    if datetime.now() > app.next_event:
        find_next_event(app)
