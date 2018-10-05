#!/usr/bin/env python
import os
import ipdb
import json
import base64

from google.cloud import pubsub_v1
from googleapiclient.discovery import build
from google.api_core import exceptions as google_exceptions
from httplib2 import Http
from oauth2client import file, client, tools

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
PROJECT_ID = 'sfdc-1538610606077'

class gapi(object):
    def __init__(self):
        super(gapi, self).__init__()
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('/Users/jamesboone/Dropbox/James Boone/credentials/sfdc_gmail_credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('gmail', 'v1', http=creds.authorize(Http()))
        self.service = service.users()
        self.subscriber = pubsub_v1.SubscriberClient()

        def get_mail(self, message):
            history_id = json.loads(message).get('historyId', {})
            if history_id:
                messages = self.service.history().list(userId='me', startHistoryId=history_id).execute()
                print 'from history: ', messages
                if messages.get('history', []):
                    if messages['history'][0].get('messages', []):
                        message_id = messages['history'][0]['messages'][0]['id']
                raw_email = self.service.messages().get(userId='me', id=message_id).execute()
                email_message = base64.urlsafe_b64decode(raw_email['payload']['parts'][0]['body']['data'].encode('UTF8'))
                print email_message

        def stop(self):
            self.service.stop(userId='me').execute()
            self.service.stop(userId='jameswboone@gmail.com').execute()

        def callback(self, message):
            print 'message in callback: ', message.data
            message.ack()
            self.get_mail(message.data)

        def sub_to_topic(self):
            topic_name = 'projects/{project_id}/topics/{topic}'.format(
                project_id=PROJECT_ID,
                topic='new_email',
            )
            subscription_name = 'projects/{project_id}/subscriptions/{sub}'.format(
                project_id=PROJECT_ID,
                sub='sub_new_email_v1',
            )
            try:
                self.subscriber.create_subscription(
                    name=subscription_name, topic=topic_name)
            except google_exceptions.AlreadyExists:
                pass
            self.subscriber.subscribe(subscription_name, callback)

        def watch(self):
            pub_topic = 'new_email'
            inbox_labels = ['INBOX']
            request = {
                "labelIds": inbox_labels,
                "topicName": "projects/{}/topics/{}".format(PROJECT_ID, pub_topic),
            }
            self.service.watch(userId='jameswboone@gmail.com', body=request).execute()
