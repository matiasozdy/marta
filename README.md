## Marta Chatbot
### Description
Marta is a slack chatbot that will fetch some readonly values from the Kubernetes api from inside the cluster.
### Creating bot in slack
Please refer to https://get.slack.help/hc/en-us/articles/115005265703-Create-a-bot-for-your-workspace
### Installing roles
kubectl create -f roles.yaml
### Generating secrets
TODO
Create a secret for the SLACK_BOT_TOKEN inside k8s.
### Running it
kubectl create -f deployment.yaml service.yaml
### Running it locally with virtualenv
Make sure you have python installed, then:
```shell
EXPORT SLACK_BOT_TOKEN=TOKEN
EXPORT ENV=dev #To use local .kube/config file.
virtualenv venv/
source venv/bin/activate
pip install -r requirements.txt
python marta.py
```
