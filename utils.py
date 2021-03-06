import apiai
import json
import requests
from pymongo import MongoClient
import urllib3
import certifi
from bs4 import BeautifulSoup
import urllib3.contrib.pyopenssl
from urllib.parse import urlparse
from urllib.parse import urlencode
from credentials import creds
urllib3.contrib.pyopenssl.inject_into_urllib3()

############################  MONGODB INTEGRATION #################################

# mongoDB client
client = MongoClient(creds['MONGODB_URI'])
db = client.get_database(creds['MONGODB_DB'])
lyric_records = db.lyric_records
http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
#urllib3.disable_warnings()

def getRECORDS(user_id):
	"""
	function to fetch all lyric searches of a user
	"""
	records = lyric_records.find({"sender_id":user_id})
	return records

def pushRECORD(record):
	"""
	function to push lyric record to collection
	"""
	lyric_records.insert_one(record)
####################################################################################

# api.ai client 
ai = apiai.ApiAI(creds['APIAI_ACCESS_TOKEN'])

# a help message
HELP_MSG = """
Hey! I am LyricBot. 
I can provide you lyrics of your favourite songs
try : Show me lyrics of despacito
"""

url_search = "http://api.musixmatch.com/ws/1.1/track.search"
search_params = {
    	"apikey":creds['MUSIX_API_KEY'],
    	"q_artist":"",
    	"q_track":"",
    	"page_size":10,
    	"page":1,
    	"s_track_rating":"desc"
		}
url_lyric = "http://api.musixmatch.com/ws/1.1/track.lyrics.get"
lyric_params = {
    	"apikey":creds['MUSIX_API_KEY'],
    	"track_id":0
		}

def get_cover_art(link):

	o = urlparse(link)
	encoded_args = urlencode({"apikey":creds['MUSIX_API_KEY']})
	url="https://"+o.netloc+o.path+"?"+encoded_args
	print(url)
	try:
		r = http.request('GET', url)
	except urllib3.exceptions.NewConnectionError:
	    print('Connection failed.')
	#r = http.request('GET', link)
	soup = BeautifulSoup(r.data,"html5lib")
	images = soup.find_all(property="og:image")
	print(r.status)
	
	try:
		image_url = images[0]['content']
	except IndexError:
		image_url = "http://s.mxmcdn.net/images-storage/albums/nocover.png"
		print("index error occured")

	return image_url


def get_lyrics(params):
	"""
	function to fetch lyrics url
	"""
	songs = []

	title = params.get("title")
#	artist = request.form.get("artist")

#	search_params['q_artist']=artist
	search_params['q_track']=title

	r = requests.get(url=url_search,params=search_params)
	data = r.json()
	song_list = data['message']['body']['track_list']
	for i in range(3):
		song = {}
		song['title'] = song_list[i]['track']['track_name']
		song['link'] = song_list[i]['track']['track_share_url']
		song['img'] = get_cover_art(song['link'])
		songs.append(song)
		
	return songs


def apiai_response(query, session_id):
	"""
	function to fetch api.ai response
	"""
	request = ai.text_request()
	request.lang='en'
	request.session_id=session_id
	request.query = query
	response = request.getresponse()
	return json.loads(response.read().decode('utf8'))


def parse_response(response):
	"""
	function to parse response and 
	return intent and its parameters
	"""
	result = response['result']
	params = result.get('parameters')
	intent = result['metadata'].get('intentName')
	return intent, params

	
def fetch_reply(query, session_id):
	"""
	main function to fetch reply for chatbot and 
	return a reply dict with reply 'type' and 'data'
	"""
	response = apiai_response(query, session_id)
	print(response)
	intent, params = parse_response(response)

	reply = {}

	
	if response['result']['action'].startswith('smalltalk'):
		reply['type'] = 'smalltalk'
		reply['data'] = response['result']['fulfillment']['speech']
		
	elif intent == "show_lyrics":
		reply = quick_response(params,session_id)

	else:
		reply['type'] = 'none'
		reply['data'] = [{"type":"postback",
						  "payload": "SHOW_HELP",
						  "title":"Click here for help!"}]

	return reply

def quick_response(params, session_id):
	reply = {}
#	params = {}
	
	reply['type'] = 'lyrics'

	songs = get_lyrics(params)

	params['sender_id'] = session_id
	# push lyric search record to mongoDB
	pushRECORD(params)

	# create generic template
	elements = []

	for song in songs:
		element = {}
		element['title'] = song['title']
		element['item_url'] = song['link']
		element['image_url'] = song['img']
		element['buttons'] = [{
			"type":"web_url",
			"title":song['title'],
			"url":song['link']}]
		elements.append(element)

	reply['data'] = elements

	return reply


