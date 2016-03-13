#!/usr/bin/env python3

from pprint import pprint
import http.cookiejar, urllib.request, urllib.parse
import json
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
import subprocess
import threading
import concurrent.futures
import os
import sys

class PresentationPlayerHTMLParser(HTMLParser):
    params = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'iframe':
            ## WTF??
            query = urllib.parse.urlparse(dict(attrs)['src']).query.encode('latin-1').replace(b'\xa7', b'&sec').decode('latin-1')
            parsed_query = urllib.parse.parse_qs(query)
            for key, value in parsed_query.items():
                self.params[key] = value[0]


cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


base = "https://echo360.e-ope.ee/ess/client"
section = "35348ebb-c8ff-429c-98fc-34f8c0be4257"


## Login
login_params = {'apiUrl':'https://echo360.e-ope.ee/ess',
                'userID':'anonymousUser',
                'token':'39f4f9968844d9cd4a0d4d46c7e4012fa2afe105f231e3f8e83800850d59202fc7f75da989f12d68cc5b49691a609da0cbfe0b39aa52d26f8727a6e93603f43f587c4a08dd2efaf975593d906ef6410d51936d89fcd6953edb2a536dd029fc0eab44a6b3788abef54b79418387a9ea2a61cb6c8575934dc6c452f946a76d738bda4c4e711636b344',
                'contentBaseUri':'https://echo360.e-ope.ee/ess'
                }
login_params = urllib.parse.urlencode(login_params)
login_url = base+"/section/"+section+'?'+login_params
login_req = opener.open(login_url)

## get videos in section
sections_url = base+"/api/sections/"+section+"/section-data.json"
r = opener.open(sections_url)

def download_rtmp(url, path):
    playpath = "/".join(urlparse(url).path.split("/")[3:])
    subprocess.call(['rtmpdump',
                    '--rtmp', 'rtmp://media.e-ope.ee/',
                    '--app', 'echo/_definst_/',
                    '--playpath', playpath,
                    '-o', path], check=True)

def download_file(url, path):
    r = opener.open(url)
    with open(path+"/"+url.split("/")[-1], 'wb') as f:
        f.write(r.read())

def download_swf(urls, path):
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:

        #future_to_url = {executor.submit(subprocess.run, ['wget', '-q', url, '-P', path], check=True): url for url in urls}
        future_to_url = {executor.submit(download_file, url, path): url for url in urls}
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

def download_presentation(params):
    xml_url = params['contentDir'] + "presentation.xml"
    print("GET", xml_url)
    r = opener.open(xml_url)
    root = ET.fromstring(r.read().decode())
    prop = root.find('presentation-properties')
    print('name:', prop.find('name').text)
    print('guid:', prop.find('guid').text)

    presentation = {
        'name': prop.find('name').text,
        'guid': prop.find('guid').text,
        'audio':None,
        'camera':None,
        'projector':[]
    }

    for group in root.findall('group'):
        for track in group:
            for data in track:
                if group.attrib['type'] == 'primary':
                    if track.attrib['type'] == 'audio' and data.attrib['type'] == 'mp3':
                        presentation['audio'] = params['contentDir'] + data.attrib['uri']
                    elif track.attrib['type'] == 'video' and data.attrib['type'] == 'flv':
                        presentation['camera'] = params['streamDir'] + data.attrib['uri']
                if group.attrib['type'] == 'projector':
                    if track.attrib['type'] == 'flash-movie' and data.attrib['type'] == 'swf':
                        presentation['projector'].append(params['contentDir'] + track.attrib['directory'] + '/' + data.attrib['uri'])
    os.makedirs("presentations/"+presentation['guid']+'/projector', exist_ok=True)
    download_swf(presentation['projector'], "presentations/"+presentation['guid']+'/projector')
    subprocess.Popen(['wget', presentation['audio'], '-P', "presentations/"+presentation['guid']])


presentations = json.loads(r.read().decode())['section']['presentations']['pageContents']
for presentation in presentations:
    print(presentation['uuid'], presentation['title'])
    pr_html = opener.open(presentation['richMedia']).read()
    parser = PresentationPlayerHTMLParser(convert_charrefs=True)
    parser.feed(pr_html.decode())
    pprint(parser.params)
    url = parser.params['contentDir']+"presentation.xml"
    download_presentation(parser.params)
