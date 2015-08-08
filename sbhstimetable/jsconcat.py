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
    print("Concatenating script/* to static/belltimes.concat.js...")
    concat_js('script')
    print("Done!")

# you can minify your own js now

