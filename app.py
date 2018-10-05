#!/usr/bin/env python
import re

from jinja2 import evalcontextfilter, Markup
from flask import Flask
import gmail_api


app = Flask(__name__, static_url_path='')


def linebreaks(value):
    """Converts newlines into <p> and <br />s."""
    value = re.sub(r'\r\n|\r|\n', '\n', value)  # normalize newlines
    paras = re.split('\n{2,}', value)
    try:
        paras = [u'<p>%s</p>' % p.encode('ascii', errors='ignore').replace('\n', '<br />') for p in paras]
    except Exception, e:
        print 'Exception: ', e
        print p
        pass
    try:
        paras = u'\n\n'.join(paras)
    except Exception, e:
        print 'Exception: ', e
        print paras
        pass
    return Markup(paras)


@app.route('/')
def read_log_file():
    with open('logfile.txt', 'r+') as f:
        file_data = f.read()
    file_data = linebreaks(file_data)
    return """
        <html>
        <header><title>Email Attachment</title></header>
        <body>
        {}
        </body>
        </html>
    """.format(file_data)


def subscribe_to_pubsub_topic(instance):
    instance.sub_to_topic()


def watch_for_email(instance):
    instance.watch()


if __name__ == "__main__":
    api = gmail_api.gapi()
    api.stop()
    subscribe_to_pubsub_topic(api)
    watch_for_email(api)
    # app.run(host='0.0.0.0', port=1337,/ debug=True)
    app.run(host='0.0.0.0', port=1337)