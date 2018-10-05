#!/usr/bin/env python
from flask import Flask
import gmail_api

app = Flask(__name__)


def subscribe_to_pubsub_topic(instance):
    instance.sub_to_topic()


def watch_for_email(instance):
    instance.stop()
    instance.watch()


if __name__ == "__main__":
    api = gmail_api.gapi()
    subscribe_to_pubsub_topic(api)
    watch_for_email(api)
    app.run(host='0.0.0.0', port=1337)
