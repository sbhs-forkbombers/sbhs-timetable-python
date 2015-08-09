import os
def concat_js(dir,out='static/belltimes.concat.js'):
    out = open(out, mode='w')
    for i in os.listdir(dir):
        i = os.path.join(dir, i)
        if os.path.isfile(i):
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
