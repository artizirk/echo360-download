#!/usr/bin/python3

import sys
import os
import subprocess
import concurrent.futures


def convert(f):
    *base, ext = f.split(".")
    base = ".".join(base)
    print(base, ext)
    os.mkfifo(base+".raw")
    subprocess.Popen(['dump-gnash', '-1', '-D', base+'.raw', f])
    subprocess.call(['gst-launch-1.0 -e filesrc location={} ! videoparse format=rgbx width=1024 height=576 framerate=24000/1000 ! videoconvert ! video/x-raw,format=NV12,framerate=24/1 ! vaapiencode_h264 tune=high-compression ! matroskamux name=mux ! filesink location={}'.format(base+'.raw',base+'.mkv')], shell=True)
    os.unlink(base+".raw")

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    future_to_url = {executor.submit(convert, f): f for f in os.listdir(".") if f.endswith(".swf")}
    for future in concurrent.futures.as_completed(future_to_url):
        url = future_to_url[future]
        try:
            data = future.result()
        except Exception as exc:
            print('%r generated an exception: %s' % (url, exc))
        else:
            print('.', end='')
            sys.stdout.flush()
    print()

    
