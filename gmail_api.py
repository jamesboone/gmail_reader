#!/usr/bin/env python

import os
import json
import base64
import ipdb
import ssl
import requests

from google.cloud import pubsub_v1
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from retrying import retry

import logging

logger = logging.getLogger('gmail_app')

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
PROJECT_ID = os.environ.get('SFDC')
EMAIL = 'me'
if not PROJECT_ID:
    raise 'No Project ID Found'


class gapi(object):
    def __init__(self):
        super(gapi, self).__init__()
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(os.environ.get('SFDC_GMAIL_CREDENTIALS'), SCOPES)
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
                        logger.debug('History ID not set from watch response, using subscriber message: {}'.format(message))
                        self.history_id = json.loads(message).get('historyId', {})
                        logger.debug('History Id set as: {}'.format(self.history_id))
                    else:
                        self.history_id = self.history.get('historyId', {})
                        logger.debug('First history id found setting self.history_id: {}'.format(self.history_id))
                    self.is_first_email = False
                else:
                    logger.debug('First email ALREADY found, using last self.history_id: {}'.format(self.history_id))
            except Exception, e:
                logger.error('Exception found: {}'.format(e))
                pass
            if self.history_id:
                messages = self.service.history().list(userId=EMAIL, startHistoryId=self.history_id).execute()
                logger.debug('From the last history id: {}, new history ids have come in: {}: '.format(self.history_id, messages))
                if isinstance(messages, list):
                    logger.debug('Messages var is a list and expected a dict')
                    ipdb.set_trace()
                if messages.get('history', []):
                    logger.debug('Message var is a dict as expected and the message history is: {}'.format(messages['history']))
                    if isinstance(messages['history'], list):
                        logger.debug('Messages history -1 is: {}'.format(messages['history'][-1]))
                    if messages['history'][-1].get('messages', []):
                        try:
                            message_id = messages['history'][-1]['messages'][0]['id']
                        except Exception, e:
                            logger.error('No message history message id was found')
                            pass
                        if message_id and message_id != self.last_message_id:
                            self.last_message_id = message_id
                            logger.debug('The message history messages Id is: {}'.format(messages['history'][-1]['messages'][0]['id']))
                            raw_email = self.service.messages().get(userId=EMAIL, id=message_id).execute()
                            if raw_email:
                                logger.debug('Raw email val: {}'.format(raw_email))
                            else:
                                logger.error('No raw email found when there should have been one.')
                        else:
                            logger.debug('This message was already processed, skipping this message, \
                                current history id: {} - current message details: {}'.format(self.history_id, messages))
                    else:
                        logger.error('No message was found when getting: "messages[\'history\'][0].get(\'messages\')"')
                elif messages.get('historyId', []):
                    logger.debug('New historyid detected, replacing old self.history_id({}) with new: {}'.format(self.history_id, messages['historyId']))
                    self.history_id = messages['historyId']
                if raw_email:
                    has_attachment = False
                    try:
                        if 'parts' in raw_email['payload']['parts'][0].keys():
                            message_contents = base64.urlsafe_b64decode(raw_email['payload']['parts'][0]['parts'][0]['body']['data'].encode('UTF8'))
                            logger.debug('Message Contents found with attachment')
                            has_attachment = True
                        elif 'body' in raw_email['payload']['parts'][0].keys():
                            message_contents = base64.urlsafe_b64decode(raw_email['payload']['parts'][0]['body']['data'].encode('UTF8'))
                            logger.debug('Message Contents found without attachment\n{}\n{}\n{}\n: '.format('*' * 20, message_contents, '*' * 20))
                    except Exception, e:
                        logger.error('Failed to collect message_contents: {}'.format(e))
                    if has_attachment:
                        try:
                            raw_email['payload']['parts'][1]['filename']  # set to filename if you would like to use
                        except Exception, e:
                            logger.error('Failed to collect filename: {}'.format(e))

                        try:
                            attachmentId = raw_email['payload']['parts'][1]['body']['attachmentId']
                        except Exception, e:
                            logger.error('Failed to collect attachmentId: {}'.format(e))

                        if attachmentId:
                            response = self.service.messages().attachments().get(userId=EMAIL, messageId=message_id, id=attachmentId).execute()
                            if response:
                                response_data = base64.urlsafe_b64decode(response['data'].encode('UTF8'))
                                if response_data:
                                    attachment_data = response_data[3:] if response_data[:3] == '\xef\xbb\xbf' else response_data
                                    with open('logfile.txt', 'w+') as f:
                                        f.write(attachment_data)
                                        logger.debug('Attachment Data: {}'.format(attachment_data))
            else:
                logger.debug('No self.history_id found...')
        except Exception, e:
            logger.error('Caught Exception 1: {}'.format(e))

        if isinstance(message, str) and not self.is_first_email:
            self.history_id = json.loads(message).get('historyId', {})
            logger.debug('Message is a string, coverting to json then setting self.history_id to: {}'.format(self.history_id))
        elif not isinstance(message, str) and not self.is_first_email:
            try:
                self.history_id = message.get('historyId', {})
                logger.debug('Message is json, setting self.history_id to: {}'.format(self.history_id))
            except Exception, e:
                logger.debug('Caught Exception 2: {}'.format(e))
        logger.debug('{}{}{}{}{}'.format('\n', '=' * 30, 'End', '=' * 30, '\n'))

    def stop(self):
        self.service.stop(userId=EMAIL).execute()
        logger.debug('Stopping Watcher')

    def callback(self, message):
        logger.debug('Message Data: {}'.format(message.data))
        try:
            response = requests.post(url='http://0.0.0.0:5000/get_mail', json=json.loads(message.data))
        except Exception, e:
            logger.error('Exception: {}'.format(e))
        logger.debug('Callback response: {}'.format(response))
        message.ack()

    def sub_to_topic(self):
        logger.debug('Starting sub_to_topic')
        # topic_name = 'projects/{project_id}/topics/{topic}'.format(
        #     project_id=PROJECT_ID,
        #     topic='new_email',
        # )
        subscription_name = 'projects/{project_id}/subscriptions/{sub}'.format(
            project_id=PROJECT_ID,
            sub='sub_new_email_v1',
        )
        # try:
        #     logger.debug('creating sub')
        #     self.subscriber.create_subscription(
        #         name=subscription_name, topic=topic_name)
        #     logger.debug('finished sub')
        # except google_exceptions.AlreadyExists:
        #     logger.debug('already exists error, passing')
        #     pass
        logger.debug('{}{}{}{}{}'.format('\n', '=' * 30, 'Starting', '=' * 30, '\n'))
        logger.debug('Subscribing to new callback')
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
            self.history = self.service.watch(userId=EMAIL, body=request).execute()
        except ssl.SSLError:
            logger.debug('\n------\nssl.SSLError, retrying\n------\n\n')
        logger.debug('Setting first history point: {}'.format(self.history))


def start():
    api = gapi()
    api.sub_to_topic()
    api.stop()
    api.watch()


if __name__ == '__main__':
    start()
