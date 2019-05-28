import os
import time
import re
import pytz
from prettytable import PrettyTable
from slackclient import SlackClient
from kubernetes import client, config
from datetime import datetime
# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "help"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
NAMESPACE = "default"
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
event $podname -> Ill output the pod events\n
logs [numlines] $podname -> Ill tail you the logs\n"""

    #List pods using the api. Need to find a way to grep. Need to try-catch.
    if command.startswith('pods'):
        try:
            ret = v1.list_namespaced_pod(NAMESPACE, watch=False)
            #resp = ['Pod - Status - Start Time']
            resp = PrettyTable(['Pod', 'Status', 'Start Time'])
            for i in ret.items:
                if len(command.split(' ', 2)) > 1:
                    if command.split(' ', 2)[1] in i.metadata.name:
                        resp.add_row([i.metadata.name, i.status.phase, i.status.start_time.strftime("%d-%b-%Y (%H:%M)")])
                else:
                    today = datetime.now(pytz.utc)
                    resp.add_row([i.metadata.name, i.status.phase, str(((today - i.status.start_time.replace(tzinfo=pytz.utc)).seconds / 60)) + ' Mins'])
                    print(type(today - i.status.start_time.replace(tzinfo=pytz.utc)))
            #response = "\n".join(resp)
            response = str(resp)
        except AssertionError as e:
            print("Error found: " + e)
            response = "An error has occured trying to list pods"
    #################################
    #Get pod logs using the api
    if command.startswith('logs'):
        try:
            if command.split(' ', 2)[1].isnumeric():
                response = v1.read_namespaced_pod_log(command.split(' ', 2)[2], NAMESPACE, tail_lines=command.split(' ', 2)[1])
            else:
                response = v1.read_namespaced_pod_log(command.split(' ', 2)[1], NAMESPACE, tail_lines=50)
        except:
            response = "An error has occured, maybe no arguments where provided after logs?"

    ################################
    #Get pod events
    if command.startswith('event'):
        try:
            resp = ['Events:']
            ret = v1.list_namespaced_event(NAMESPACE, field_selector='involvedObject.name=' + command.split(None, 1)[1])
            for i in ret.items:
                resp.append(i.message)
            response = "\n".join(resp)
        except:
            response = "An error has occured or no events found for pod"
    ################################
    #Get deployments or specific deployment image    
    if command.startswith('deploy'):
        try:
            v1apps = client.AppsV1Api()
            resp = PrettyTable(['Name','Available replicas', 'Desired replicas', 'Image'])
            if len(command.split(' ', 2)) > 1:
                ret = v1apps.read_namespaced_deployment(command.split(' ', 2)[1], NAMESPACE)
                resp.add_row([ret.metadata.name, ret.status.available_replicas, ret.status.replicas, ret.spec.template.spec.containers[0].image])
            else:
                ret = v1apps.list_namespaced_deployment(NAMESPACE)
                for i in ret.items:
                    today = datetime.now(pytz.utc)
                    resp.add_row([i.metadata.name, i.status.available_replicas, i.status.replicas, i.spec.template.spec.containers[0].image])
            response = str(resp)
        except AssertionError as e:
            print("Error found: " + e)
            response = "An error has occured trying to get deployments"


    # Sends the response back to the channel
    if len(response) > 4000:
        ftext=response
    else:
        ftext='```' + response + '```'
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=ftext or default_response
    )



if __name__ == "__main__":

    #If is for local testing, read the kubeconfig file
    if os.environ.get('ENV') == 'dev':
        print("Using local kubeconfig file")
        config.load_kube_config()
    else:
    #Actually loading kube_token from inside the cluster if it's a pod
        config.load_incluster_config()

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
