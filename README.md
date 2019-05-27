## Marta Chatbot
### Description
Marta is a slack chatbot that will fetch some readonly values from the Kubernetes api from inside the cluster.
### Creating bot in slack
### Installing roles
### Generating secrets
### Running it
### Running it locally with virtualenv
Make sure you have python installed, then:
```shell
EXPORT SLACK_BOT_TOKEN=TOKEN
virtualenv venv/
source venv/bin/activate
pip install -r requirements.txt
python marta.py
```
