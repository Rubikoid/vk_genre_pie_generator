#!/usr/bin/python2
# -*- coding: utf-8 -*-

from robobrowser import RoboBrowser
import requests, pickle, json, urllib, urllib2, HTMLParser, re, os, sys, urlparse
import pygn, show
import config

current_client_id = config.vk_app_client_id
current_client_secret = config.vk_app_client_secret
# file, where auth data is saved
AUTH_FILE = '.auth_data'
# chars to exclude from filename. Not used.
FORBIDDEN_CHARS = '/\\\?%*:|"<>!'

theAudioDBUrl = 'http://www.theaudiodb.com/api/v1/json/'+config.audioDBKey+'/searchtrack.php?{end}'
lastFMUrl = 'http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key='+config.lastFMKey+'&format=json&{end}'
gracenote_client_id = config.gracenoteAPIKey
gracenote_user_id = pygn.register(gracenote_client_id)

class VKUrlOpener(urllib.FancyURLopener):
    version = config.vk_app_useragent

urllib._urlopener = VKUrlOpener()

def utf8_urlencode(params):
    # problem: u.urlencode(params.items()) is not unicode-safe. Must encode all params strings as utf8 first.
    # UTF-8 encodes all the keys and values in params dictionary
    for k,v in params.items():
        # TRY urllib.unquote_plus(artist.encode('utf-8')).decode('utf-8')
        if type(v) in (int, long, float):
            params[k] = v
        else:
            try:
                params[k.encode('utf-8')] = v.encode('utf-8')
            except Exception as e:
                logging.warning( '**ERROR utf8_urlencode ERROR** %s' % e )
    return urllib.urlencode(params.items()).decode('utf-8')

def get_saved_auth_params():
    access_token = None
    user_id = None
    try:
        with open(AUTH_FILE, 'rb') as pkl_file: 
            access_token = pickle.load(pkl_file)
            user_id = pickle.load(pkl_file)
    except IOError:
        pass
    return access_token, user_id

def save_auth_params(access_token, user_id):
    with open(AUTH_FILE, 'wb') as output:
        pickle.dump(access_token, output)
        pickle.dump(user_id, output)
    os.chmod(AUTH_FILE, 700)

def get_auth_params():
    login = raw_input("Your login: ")
    password = raw_input("Your password: ")
    auth_url = ("https://api.vk.com/oauth/token?grant_type=password&v=5.77&scope=status,friends,photos,audio,video,docs,notes,pages,wall,groups,notifications,messages,market&client_id={cli_id}&client_secret={cli_sec}"
        "&username={login}&password={password}".format(cli_id=current_client_id,cli_sec=current_client_secret,login=login, password=password))
    browser = RoboBrowser(history=True)
    browser.open(auth_url)
    if 'error' in browser.response.text:
        if '2fa_app' in browser.response.text:
            redirect_url = json.loads(str(browser.response.text))["redirect_uri"]
            browser.open(redirect_url)
            twoFA = raw_input("2factor need, code: ")
            form = browser.get_form()
            form['code'] = twoFA
            browser.submit_form(form)
    if 'success=1' in browser.response.url:
        redirected_url = browser.response.url
    else:
        print(browser.parsed)
        sys.exit()
    aup = urlparse.parse_qs(redirected_url)
    save_auth_params(aup['access_token'][0], aup['user_id'][0])
    return aup['access_token'][0], aup['user_id'][0]

def get_tracks_metadata(access_token, user_id):
    code = 'return {audios:API.audio.get({"owner_id":'+str(user_id)+',"offset":0,"count":9999})};'
    code = urllib.quote(code, safe='')
    url = ("https://api.vk.com//method/execute?"
        "code={code}&access_token={atoken}&v=5.77".format(atoken=access_token, code=code))
    req = urllib2.Request(url, headers={ 'User-Agent': config.vk_app_useragent })
    audio_get_page = urllib2.urlopen(req).read()
    rj = json.loads(audio_get_page)
    if 'execute_errors' in rj:
        if rj['execute_errors'][0]['error_code'] == 25:
            new_token = refresh_token(access_token)
            save_auth_params(new_token, user_id)
            return get_tracks_metadata(new_token, user_id)
        else:
            print('ERROR: {0}'.format(rj))
    else:
        return json.loads(audio_get_page)['response']['audios']["items"]

def refresh_token(token):
    print('REFRESHING TOKEN')
    url = ("https://api.vk.com/method/auth.refreshToken")
    data = urllib.urlencode({'access_token' : token, 'v'  : '5.77', 'receipt': config.magic_constant_sniffed_from_vk})
    req = urllib2.Request(url, data, headers={ 'User-Agent': config.vk_app_useragent})
    refresh_post_page = urllib2.urlopen(req).read()
    return json.loads(refresh_post_page)['response']['token']
    
def clearText(text, pars):
    text = pars.unescape(text).strip()
    #text = (text[:100]).strip()
    #text = re.sub('[' + FORBIDDEN_CHARS + ']', "", text)
    #text = re.sub(' +', ' ', text)
    return text
    
def get_track_full_name(t_data):
    html_parser = HTMLParser.HTMLParser()
    return (clearText(t_data['artist'], html_parser), clearText(t_data['title'], html_parser))
   
def getAllTags():
    tags = {}
    access_token, user_id = get_saved_auth_params()
    if not access_token or not user_id:
        access_token, user_id = get_auth_params()
    tracks = get_tracks_metadata(access_token, user_id)
    print('Prepare end, going over tracks')
    for t in tracks:
        t_name = get_track_full_name(t)
        tag = check(t_name[0], t_name[1])
        for i in tag:
            if i in tags:
                tags[i] += 1
            else:
                tags[i] = 1
    print("All music checked, tags: ")
    print(tags)
    return tags
  
def checkAuDB(art, track):
    ru = theAudioDBUrl.format(end = utf8_urlencode({'s':art, 't':track}))
    r = requests.get(ru)
    tags = []
    rj = r.json()
    if rj['track'] is None:
        print('Tags not found for {0}: {1}'.format(art.encode('utf-8'), track.encode('utf-8')))
        return ['nan']
    if len(rj['track']) > 1:
        print('WOOW for {0}: {1}'.format(art.encode('utf-8'), track.encode('utf-8')))
    tags.append(rj['track'][0]['strGenre'])
    return tags    
    
def checkLastFM(art, track):
    ru = lastFMUrl.format(end = utf8_urlencode({'artist':art, 'track':track}))
    r = requests.get(ru)
    tags = []
    rj = r.json()
    if 'track' not in rj:
        print('Tags not found for {0}: {1}'.format(art.encode('utf-8'), track.encode('utf-8')))
        return ['nan']
    for i in rj['track']['toptags']['tag']:
        tags.append(i['name'])
    return tags
    
def checkGN(art, track):
    tags = []
    rj = pygn.search(clientID=gracenote_client_id, userID=gracenote_user_id, artist=art, track=track)
    if rj is None:
        print('Dead song found - {0}: {1}'.format(art.encode('utf-8'), track.encode('utf-8')))
        return ['non']
    #Gracenote return too much info, he can found song with absolutly random name, so i need to make this shitcode.
    #Maybe normal solution can exsist, but idk how to make it without fucking my brain
    if rj['tracks'][0]['track_title'] != track:
        print('Strange song found - {0}: {1}. Catched: {2}'.format(art.encode('utf-8'), track.encode('utf-8'), rj['tracks'][0]['track_title'].encode('utf-8')))
        #a = raw_input('More info?(Y/Any):')
        #if a == 'Y':
        #    print(rj)
        #a = raw_input('Kill that?(Y/Any):')
        #if a == 'Y':
        #return ['nan']
    #print("{0}: {1} (?) {2}".format(art.encode('utf-8'), track.encode('utf-8'), rj['tracks'][0]['track_title'].encode('utf-8')))
    for k in rj['genre']:
        tags.append(rj['genre'][k]['TEXT'])
    return tags
 

checkers = [
    ('LastFM',checkLastFM),
    ('TheAudioDB', checkAuDB),
    ('GraceNode', checkGN)
]
check = None

def selectCheck(): #a bit dirty, but i don't want to think about more clear solution
    global check
    if check is None:
        print('Select checker: ')
        for i in range(0, len(checkers)):
            print('{0}. {1}'.format(i+1, checkers[i][0]))
        a = int(raw_input()) - 1
        if a < 0 or a >= len(checkers):
            print('Select valid checker')
            sys.exit(0)
        else:
            check = checkers[a][1]
            return checkers[a][0]
 
#check = checkLastFM
#check = checkAuDB
#check = checkGN
    
def main():
    checkerName = selectCheck()
    tracks = getAllTags()
    show.magic(tracks, name = 'Music statistic (using {0}, w/o 1-2)'.format(checkerName))
    
if __name__ == '__main__':
    main()