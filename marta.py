import os
import time
import re
from slackclient import SlackClient
from kubernetes import client, config

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "help"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Define k8s client constants
    """
    v1 = client.CoreV1Api()

    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)

    response = None

    if command.startswith(EXAMPLE_COMMAND):
        response = """I can provide you with diferent information from the current k8s cluster im running\n
pods [part of name] -> Ill provide you a list of available pods\n
describe $podname -> Ill output the pod description\n
logs [numlines] $podname -> Ill tail you the logs\n"""

    #List pods using the api. Need to find a way to grep. Need to try-catch.
    if command.startswith('pods'):
        ret = v1.list_namespaced_pod('default', watch=False)
        resp = ['Pod - Status - Start Time']
        for i in ret.items:
            resp.append(i.metadata.name + ' - ' + i.status.phase + ' - ' + i.status.start_time.strftime("%d-%b-%Y (%H:%M)"))
        response = "\n".join(resp)
    #################################
    #Get pod logs using the api
    if command.startswith('logs'):
        if command.split(' ', 2)[1].isnumeric():
            response = v1.read_namespaced_pod_log(command.split(' ', 2)[2], 'default', 'tail_lines=' + command.split(' ', 2)[1])
        else:
            response = v1.read_namespaced_pod_log(command.split(' ', 2)[2], 'default', 'tail_lines=50')

    ################################
    #Get pod events
    if command.startswith('desc'):
        resp = ['Events:']
        ret = v1.list_namespaced_event('default', field_selector='involvedObject.name=' + command.split(None, 1)[1])
        for i in ret.items:
            resp.append(i.message)
        response = "\n".join(resp)
    ################################
   
    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )



if __name__ == "__main__":
    #This is for local testing using kube_config
    config.load_kube_config()
    #Actually loading kube_token from inside the cluster
    #config.load_incluster_config()
    if slack_client.rtm_connect(with_team_state=False):
        print("Marta connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
