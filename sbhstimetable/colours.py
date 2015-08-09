# sbhs-timetable-python
# Copyright (C) 2015 Simon Shields, James Ye
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from urllib.parse import quote_plus as urlencode

COLOURS = {
    'purple': {
        'fg': '#b388ff',
        'bg': '#000000',
        'highBg': '#fff9c4',
        'highFg': '#8bc34a'
    },
    'default': {
        'fg': '#ffffff',
        'bg': '#000000',
        'highBg': '#e51c23',
        'highFg': '#ffc107'
    },
    'red': {
        'fg': '#e84e40',
        'bg': '#000000',
        'highBg': '#5af158',
        'highFg': '#cddc39'
    },
    'green': {
        'fg': '#8bc34a',
        'bg': '#000000',
        'highBg': '#bf360c',
        'highFg': '#ffeb3b'
    }
}


class Colour:
    def __init__(self, obj):
        self.data = obj
        self.bg = self.data['bg']
        self.fg = self.data['fg']
        self.highBg = self.data['highBg']
        self.highFg = self.data['highFg']

    def __str__(self):
        return '?bg=' + urlencode(self.data['bg']) + '&fg=' + urlencode(self.data['fg']) + '&highBg=' + urlencode(self.data['highBg']) + '&highFg=' + urlencode(self.data['highFg'])



def get(name, invert):
    res = COLOURS['default']
    if name in COLOURS:
        res = COLOURS[name]
    if invert:
        (res['fg'],res['bg']) = (res['bg'],res['fg'])
        (res['highFg'],res['highBg']) = (res['highBg'],res['highFg'])
    return Colour(res)


def get_from_qs(query):
    defs = COLOURS['default']
    res = {}
    for i in defs:
        if i not in query:
            res[i] = defs[i]
        else:
            if query[i][0] != '#':
                res[i] = '#' + query[i]
            else:
                res[i] = query[i]
    return Colour(res)
