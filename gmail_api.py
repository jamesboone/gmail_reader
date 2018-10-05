#!/usr/bin/env python
import json
import base64
import ipdb
import ssl

from google.cloud import pubsub_v1
from googleapiclient.discovery import build
from google.api_core import exceptions as google_exceptions
from httplib2 import Http
from oauth2client import file, client, tools
from retrying import retry

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
        self.history = None
        self.history_id = None
        self.is_first_email = True
        self.last_message_id = None

    def get_mail(self, message):
        raw_email = None
        attachmentId = None
        response = None
        response_data = None
        messages = None
        try:
            try:
                if self.is_first_email:
                    if not self.history and isinstance(message, str):
                        print '\nHistory ID not set from watch response, using subscriber message: ', message
                        self.history_id = json.loads(message).get('historyId', {})
                        print '\nHistory Id set as: ', self.history_id
                    else:
                        self.history_id = self.history.get('historyId', {})
                        print '\nFirst history id found setting self.history_id: ', self.history_id
                    self.is_first_email = False
                else:
                    print '\nFirst email ALREADY found, using last self.history_id: ', self.history_id
            except Exception, e:
                print '\nException found: ', e
                pass
            if self.history_id:
                messages = self.service.history().list(userId='me', startHistoryId=self.history_id).execute()
                print '\nFrom the last history id: {}, new history ids have come in: {}: '.format(self.history_id, messages)
                if isinstance(messages, list):
                    print '\nMessages var is a list and expected a dict'
                    ipdb.set_trace()
                if messages.get('history', []):
                    print '\nMessage var is a dict as expected and the message history is: ', messages['history']
                    if isinstance(messages['history'], list):
                        print '\nMessages history -1 is: ', messages['history'][-1]
                    if messages['history'][-1].get('messages', []):
                        try:
                            message_id = messages['history'][-1]['messages'][0]['id']
                        except Exception, e:
                            print '\nNo message history message id was found'
                            ipdb.set_trace()
                            pass
                        if message_id and message_id != self.last_message_id:
                            self.last_message_id = message_id
                            print '\nThe message history messages Id is: ', messages['history'][-1]['messages'][0]['id']
                            raw_email = self.service.messages().get(userId='me', id=message_id).execute()
                            if raw_email:
                                # print '\nraw_email was found and is this long: ', len(raw_email)
                                print '\nRaw email val: ', raw_email
                            else:
                                print '\nNo raw email found when there should have been one.'
                                ipdb.set_trace()
                                print
                        else:
                            print '\nThis message was already processed, skipping this message'
                            print '\nCurrent history id: ', self.history_id, ' - current message details: ', messages
                    else:
                        print '\nNo message was found when getting: "messages[\'history\'][0].get(\'messages\')"'
                        ipdb.set_trace()
                        print
                elif messages.get('historyId', []):
                    print '\nNew historyid detected, replacing old self.history_id({}) with new: {}'.format(self.history_id, messages['historyId'])
                    self.history_id = messages['historyId']
                if raw_email:
                    has_attachment = False
                    try:
                        if raw_email['payload']['parts'][0].has_key('parts'):
                            message_contents = base64.urlsafe_b64decode(raw_email['payload']['parts'][0]['parts'][0]['body']['data'].encode('UTF8'))
                            print '\nMessage Contents found with attachment'
                            has_attachment = True
                        elif raw_email['payload']['parts'][0].has_key('body'):
                            message_contents = base64.urlsafe_b64decode(raw_email['payload']['parts'][0]['body']['data'].encode('UTF8'))
                            print '\nMessage Contents found without attachment\n{}\n{}\n{}\n: '.format('*' * 20, message_contents, '*' * 20)
                    except Exception, e:
                        print '\nFailed to collect message_contents: ', e
                        ipdb.set_trace()
                        pass
                    if has_attachment:
                        try:
                            filename = raw_email['payload']['parts'][1]['filename']
                        except Exception, e:
                            print '\nFailed to collect filename: ', e
                            ipdb.set_trace()
                            pass
                        try:
                            attachmentId = raw_email['payload']['parts'][1]['body']['attachmentId']
                        except Exception, e:
                            print '\nFailed to collect attachmentId: ', e
                            ipdb.set_trace()
                            pass

                        if attachmentId:
                            response = self.service.messages().attachments().get(userId='me', messageId=message_id, id=attachmentId).execute()
                            if response:
                                response_data = base64.urlsafe_b64decode(response['data'].encode('UTF8'))
                                if response_data:
                                    attachment_data = response_data[3:] if response_data[:3] == '\xef\xbb\xbf' else response_data
                                    with open('logfile.txt', 'w+') as f:
                                        f.write(attachment_data)
                                        print 'attachment_data: ', attachment_data
            else:
                print '\nNo self.history_id found...'
                ipdb.set_trace()
                print
        except Exception, e:
            print '\nCaught Exception 1: ', e

            pass
        if isinstance(message, str) and not self.is_first_email:
            self.history_id = json.loads(message).get('historyId', {})
            print '\nMessage is a string, coverting to json then setting self.history_id to: ', self.history_id
        elif not isinstance(message, str) and not self.is_first_email:
            try:
                self.history_id = message.get('historyId', {})
                print '\nMessage is json, setting self.history_id to: ', self.history_id
            except Exception, e:
                print '\nCaught Exception 2: ', e
                pass
        print '\n', '=' * 30, 'End', '=' * 30, '\n'

    def stop(self):
        self.service.stop(userId='me').execute()
        self.service.stop(userId='jameswboone@gmail.com').execute()
        print '\nStopping Watcher'

    def callback(self, message):
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
        print '\n', '=' * 30, 'Starting', '=' * 30, '\n'
        print 'Subscribing to new callback'
        self.subscriber.subscribe(subscription_name, self.callback)

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=60000,
           retry_on_exception=ssl.SSLError, stop_max_attempt_number=5)
    def watch(self):
        pub_topic = 'new_email'
        inbox_labels = ['UNREAD']
        request = {
            "labelIds": inbox_labels,
            "topicName": "projects/{}/topics/{}".format(PROJECT_ID, pub_topic),
            "labelFilterAction": "include"
        }
        try:
            self.history = self.service.watch(userId='jameswboone@gmail.com', body=request).execute()
        except ssl.SSLError:
            print '\n\n------\nssl.SSLError, retrying\n------\n\n'
        print '\nSetting first history point: ', self.history


# if __name__ == '__main__':
#     api = gapi()
#     api.sub_to_topic()
#     api.stop()
#     api.watch()
#     print 'watching'
