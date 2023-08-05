import slack
import os
from dotenv import load_dotenv
from flask import Flask, request
from slackeventsapi import SlackEventAdapter
import json

app = Flask(__name__)
load_dotenv()

import sys
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

from actions import give_bit, remove_bit, get_leaderboard, set_team, set_team_action_handler, print_team_leaderboard, get_help
from helper import extract_user_id

client = slack.WebClient(
    token=os.environ["SLACK_BOT_TOKEN"]
)

slack_event_adapter = SlackEventAdapter(
    os.environ["SLACK_SIGNING_SECRET"],
    '/slack/events',
    app
)

valid_channels = [
    os.environ['BOT_LOGS_CHANNEL'],
]
    
Action = {
    "GIVE": "give",
    "REMOVE":  "remove",
    "LEADERBOARD":  "leaderboard",
    "SET_TEAM": "set-team",
    "TEAM_LEADERBOARD": "team-leaderboard",
    "HELP": "help"
}
ActionNameToAction = {
    Action.get("GIVE"): give_bit,
    Action.get("REMOVE"): remove_bit,
    Action.get("LEADERBOARD"): get_leaderboard,
    Action.get("SET_TEAM"): set_team,
    Action.get("TEAM_LEADERBOARD"): print_team_leaderboard,
    Action.get("HELP"): get_help
}

BOT_ID = client.api_call("auth.test")["user_id"]

@app.route('/health')
def health():
    return {"health": os.environ["ENV_TEST"]}

@app.route('/slack/events', methods=['POST'])
def handle_challenge():
    return {"challenge": request.json()['challenge']}

@app.route('/slack/events/interactivity', methods=['POST'])
def handle_interactivity():
    try:
        message = json.loads(request.form.get("payload"))
        action = message.get("actions")[0].get("action_id")
        user_id = message.get("user").get('id')

        if action == "select_team_action":
            selected_option = message.get("actions")[0].get('selected_option').get('value')
            set_team_action_handler(client, selected_option, user_id)
        return {}
    except Exception as e:
        client.chat_postMessage(
            channel=os.environ["BOT_LOGS_CHANNEL"],
            text=f"<@{user_id}>: an exception occurred - {e}"
        )


@slack_event_adapter.on('app_mention')
def app_mention(payload):
    try:
        event = payload.get('event', {})
        channel_id = event.get('channel')
        timestamp = event.get('ts')
        user_id = event.get('user')

        if channel_id not in valid_channels:
            return

        text = event.get('text')
        arguments = text.split(' ')
        bot_id = extract_user_id(arguments[0])
        if bot_id != BOT_ID:
            return;

        action = arguments[1]
        if action not in Action.values():
            client.chat_postMessage(
                channel=os.environ["BOT_LOGS_CHANNEL"],
                text=f"<@{user_id}>: {action} is not a valid action"
            )
            raise Exception(f"{action} is not a valid action")
        
        ActionNameToAction[action](client, arguments, user_id, channel_id)

        client.reactions_add(
            channel=channel_id,
            timestamp=timestamp,
            name="white_check_mark"
        )  
    except Exception as e:
        client.chat_postMessage(
            channel=os.environ["BOT_LOGS_CHANNEL"],
            text=f"<@{user_id}>: an exception occurred - {e}"
        )
        client.reactions_add(
                channel=channel_id,
                timestamp=timestamp,
                name="x"
            )        

@slack_event_adapter.on('message')
def message_im(payload):
    try:        
        event = payload.get('event', {})
        if event.get('channel_type') != 'im':
            return
        
        timestamp = event.get('ts')
        user_id = event.get('user')
        channel_id = event.get("channel")

        text = event.get('text')
        arguments = text.split(' ')
        bot_id = extract_user_id(arguments[0])

        if user_id == BOT_ID:
            return
        
        if bot_id != BOT_ID:
            return;

        action = arguments[1]
        if action not in Action.values():
            client.chat_postMessage(
                channel=os.environ["BOT_LOGS_CHANNEL"],
                text=f"<@{user_id}>: {action} is not a valid action"
            )
            raise Exception(f"{action} is not a valid action")
        
        ActionNameToAction[action](client, arguments, user_id, channel_id)

        client.reactions_add(
            channel=channel_id,
            timestamp=timestamp,
            name="white_check_mark"
        )  
    except Exception as e:
        client.chat_postMessage(
            channel=os.environ["BOT_LOGS_CHANNEL"],
            text=f"<@{user_id}>: an exception occurred - {e}"
        )
        client.reactions_add(
                channel=channel_id,
                timestamp=timestamp,
                name="x"
            )        

if __name__ == "__main__":
    app.run(debug=True)