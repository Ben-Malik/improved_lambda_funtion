import json
import os
from requests.auth import HTTPBasicAuth
import time
import requests
import base64
from threading import Thread

key = os.environ['auth_key']
auth = HTTPBasicAuth('Authorization', key)

def parse_text(text):
    return [i.split('=') for i in text.split('&') if i.startswith('text=')][0][1]
    
def get_response_url(text):
    return [i.split('=') for i in text.split('&') if i.startswith('response_url=')][0][1]

def post_response_to_slack(thread_id, response_url):
    r = requests.get(
            url=f'https://api.openai.com/v1/threads/{thread_id}/messages',
            headers={'Content-Type': 'application/json', 'OpenAI-Beta': 'assistants=v2'},
            auth=auth
        )
    
    ret = json.loads(r.text)
    data = ret['data']
    data_as_json = json.dumps(data[0]['content'][0]['text']['value']).replace('**', '*').replace('\"', '').replace('\\n', '')
      
    slack_data = {'text': data_as_json}

    # Post output response to slack using the response url
    response = requests.post(response_url,data=json.dumps(slack_data), headers={'Content-Type': 'application/json'})    
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )

def lambda_handler(event, context):

    body = str(base64.b64decode(event['body']))
    quoted_url = get_response_url(body)
    response_url = requests.utils.unquote(quoted_url)

    # question = body.get('question', "What colour is air?")
    question = parse_text(body)
    
    
    # create a thread
    r = requests.post(
        url='https://api.openai.com/v1/threads',
        headers = {'Content-Type': 'application/json', 'OpenAI-Beta': 'assistants=v2'},
        auth=auth,
        json={}
    )
        
    thread_id = json.loads(r.text)['id']
        
    # create a message to the above thread
    r = requests.post(
        url=f'https://api.openai.com/v1/threads/{thread_id}/messages',
        headers={'Content-Type': 'application/json', 'OpenAI-Beta': 'assistants=v2'},
        auth=auth,
        json={
            "role": "user",
            "content": question # "When were the northern lights visible in NL?"
        }
    )
         
    # create a run from the above thread
    r = requests.post(
        url=f'https://api.openai.com/v1/threads/{thread_id}/runs',
        headers={'Content-Type': 'application/json', 'OpenAI-Beta': 'assistants=v2'},
        auth=auth,
        json={
            "assistant_id": "asst_HM1Gd4b51r2TbFPPH7PJQeRm",
            "instructions": "Use you knowledge base to answer questions."
        }
    )
    
    thr = Thread(target=post_response_to_slack, args=[thread_id,response_url])
    thr.start()
    
    return {
        'statusCode': 200,
        'body' : 'Just a moment, I am processing my knowledge'
    }
