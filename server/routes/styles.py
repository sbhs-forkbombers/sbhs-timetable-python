import flask
import sbhstimetable.colours as colours

from flask import make_response
from scss.compiler import Compiler
from scss.namespace import Namespace
from scss.types import Color
from server import app
from server.util import etagged

@etagged
@app.route('/style/index.css')
def customise_css():
    colour = colours.get_from_qs(flask.request.args)
    namespace = Namespace()
    namespace.set_variable('$fg', Color.from_hex(colour.fg))
    namespace.set_variable('$bg', Color.from_hex(colour.bg))
    namespace.set_variable('$highFg', Color.from_hex(colour.highFg))
    namespace.set_variable('$highBg', Color.from_hex(colour.highBg))

    compiler = Compiler(namespace=namespace)
    res = make_response(compiler.compile('style/index.scss'))
    res.mimetype = 'text/css'
    return res