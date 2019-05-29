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
    v1apps = client.AppsV1Api()

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
logs [numlines] $podname -> Ill tail you the logs\n
deploy [$deploymentname] -> Will display a list of current deployments with it's image version for container[0]

"""
    
    #################################
    #List pods
    if command.startswith('pods'):
        try:
            ret = v1.list_namespaced_pod(NAMESPACE, watch=False)
            resp = PrettyTable(['Pod', 'Status', 'Age'])
            for i in ret.items:
                today = datetime.now(pytz.utc)
                ###Parse time correctly
                runningtime = (today - i.status.start_time.replace(tzinfo=pytz.utc))
                temptime = runningtime.seconds % (24 * 3600)
                hours = temptime // 3600
                temptime %= 3600
                minutes = temptime // 60
                temptime %= 60
                secs = temptime
                if (hours >= 24):
                    runt = str(runningtime.days) + 'D ' + str(hours) + 'h ' + str(minutes) + 'm ' + str(secs) + 's'
                else:
                    runt = str(hours) + 'h ' + str(minutes) + 'm ' + str(secs) + 's'
                    if ((hours < 1)):
                        runt = str(minutes) + 'm ' + str(secs) + 's'
                        if (minutes < 1):
                            runt = str(secs) + 's'

                if len(command.split(' ', 2)) > 1:
                    if command.split(' ', 2)[1] in i.metadata.name:
                        resp.add_row([i.metadata.name, i.status.phase, runt])
                else:
                    resp.add_row([i.metadata.name, i.status.phase, runt])
            response = str(resp)
        except AssertionError as e:
            print("Error found: " + e)
            response = "An error has occured trying to list pods"

    #################################
    #Get pod logs
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

    ################################
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
