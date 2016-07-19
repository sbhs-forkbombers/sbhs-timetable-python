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
import os
def concat_js(dir,out='static/belltimes.concat.js'):
    out = open(out, mode='w')
    for i in sorted(os.listdir(dir)):
        i = os.path.join(dir, i)
        if os.path.isfile(i) and i.endswith('.js') and not i.endswith('.concat.js'):
            with open(i) as f:
                for l in f:
                    out.write(l)
            out.write(';')
    out.close()

if __name__ == "__main__":
    import yaml
    print("Concatenating script/* to static/belltimes.concat.js...")
    concat_js('script')
    print("Done!")
    with open('config.yml') as c:
        cfg = yaml.load(c)
    if cfg['comp']['java_exe']:
        import closure, subprocess
        cl_path = closure.get_jar_filename()
        print("Minifying javascript using closure compiler at " + cl_path + "...")
        subprocess.call([cfg['comp']['java_exe'], '-jar', cl_path, '--js', 'static/belltimes.concat.js',
                  '--js_output_file=static/belltimes.concat.js', '--compilation_level', 'SIMPLE_OPTIMIZATIONS',
                  '--language_in', 'ECMASCRIPT5_STRICT'])
        print("Done!")
