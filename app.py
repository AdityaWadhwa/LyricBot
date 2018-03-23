from flask import Flask, request
from pymessenger import Bot
from utils import fetch_reply, quick_response, HELP_MSG
import requests,json

app = Flask("My lyric bot")

VERIFICATION_TOKEN = "hello"


FB_ACCESS_TOKEN = "EAAMOWZAcleDIBAOY7lQajyt9Tze4S0K3Rh5879kAQ0MfsKk7Vg2N3q3sxJUjdXKZAZCZARnXZAm8q5VgB85O9VUdBMY2Lov38ZAFupf3GOjImcm47SHfMr4DWQWe2lbz4kfB0nhFD3v0RjQvDev6Y6szHelW89NiM98xvfR6pGadSUn5rPx2DW"
bot = Bot(FB_ACCESS_TOKEN)


@app.route('/', methods=['GET'])
def verify():
	if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
		if not request.args.get("hub.verify_token") == VERIFICATION_TOKEN:
			return "Verification token mismatch", 403
		return request.args["hub.challenge"], 200
	set_persistent_menu()
	set_greeting_text()
	set_get_started()
	return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():
	
	data = request.get_json()

	if data['object'] == "page":
		entries = data['entry']

		for entry in entries:
			messaging = entry['messaging']

			for messaging_event in messaging:

				sender_id = messaging_event['sender']['id']
				recipient_id = messaging_event['recipient']['id']

				bot.send_action(sender_id, "mark_seen")

				if messaging_event.get('message'):
					# HANDLE NORMAL MESSAGES HERE

					if messaging_event['message'].get('text'):
						# HANDLE TEXT MESSAGES

						query = messaging_event['message']['text']

						bot.send_action(sender_id, "typing_on")

						reply = fetch_reply(query, sender_id)
				
						if reply['type'] == 'lyrics':
							bot.send_generic_message(sender_id, reply['data'])

						elif reply['type'] == 'none':
							bot.send_button_message(sender_id, "Sorry, I didn't understand. :(", reply['data'])

						else:
							bot.send_text_message(sender_id, reply['data'])					

						
				elif messaging_event.get('postback'):
					# HANDLE POSTBACKS HERE
					
					payload = messaging_event['postback']['payload']
					if payload ==  'SHOW_HELP':
						bot.send_text_message(sender_id, HELP_MSG)	
				bot.send_action(sender_id, "typing_off")
	print(reply['data'])
	return "Success", 200


def set_greeting_text():
	headers = {
		'Content-Type':'application/json'
		}
	data = {
		"setting_type":"greeting",
		"greeting":{
			"text":"Hi {{user_first_name}}! I am lyric bot"
			}
		}
	ENDPOINT = "https://graph.facebook.com/v2.8/me/thread_settings?access_token=%s"%(FB_ACCESS_TOKEN)
	r = requests.post(ENDPOINT, headers = headers, data = json.dumps(data))
	print(r.content)

def set_persistent_menu():
	headers = {
		'Content-Type':'application/json'
		}
	data = {
		"setting_type":"call_to_actions",
		"thread_state" : "existing_thread",
		"call_to_actions":[
			{
				"type":"web_url",
				"title":"Meet the developer",
				"url":"https://www.facebook.com/aditya.wadhwa13" 
			},
			{
				"type":"postback",
				"title":"Help",
				"payload":"SHOW_HELP"
			}]
		}
	ENDPOINT = "https://graph.facebook.com/v2.8/me/thread_settings?access_token=%s"%(FB_ACCESS_TOKEN)
	r = requests.post(ENDPOINT, headers = headers, data = json.dumps(data))
	print(r.content)

def set_get_started():
	headers = {
		'Content-Type':'application/json'
		}
	data = {
		"setting_type":"call_to_actions",
		"thread_state":"new_thread",
		"call_to_actions":[{
    		"payload":"SHOW_HELP"
  			}]
  		}
	ENDPOINT = "https://graph.facebook.com/v2.8/me/thread_settings?access_token=%s"%(FB_ACCESS_TOKEN)
	r = requests.post(ENDPOINT, headers = headers, data = json.dumps(data))
	print(r.content)

if __name__ == "__main__":
	app.run(port=8000)