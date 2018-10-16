#!/usr/bin/env python
import re

from jinja2 import Markup
from flask import Flask, request
import gmail_api
import logging

app = Flask(__name__)
logger = logging.getLogger('main_app')
app.gmail_api = gmail_api.gapi()


def linebreaks(value):
    """Converts newlines into <p> and <br />s."""
    value = re.sub(r'\r\n|\r|\n', '\n', value)  # normalize newlines
    paras = re.split('\n{2,}', value)
    try:
        paras = [u'<p>%s</p>' % p.encode('ascii', errors='ignore').replace('\n', '<br />') for p in paras]
    except Exception, e:
        logger.error('Exception: {}'.format(e))
        pass
    try:
        paras = u'\n\n'.join(paras)
    except Exception, e:
        logger.error('Exception: {}'.format(e))
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


@app.route('/get_mail', methods=['POST'])
def get_mail():
    logger.debug('request.data: {}'.format(request.data))
    app.gmail_api.get_mail(request.data)
    return str(200)


@app.route('/start')
def start():
    logger.info('Initializing API')
    gmail_api.start()
    return str(200)


app.gmail_api.sub_to_topic()
app.gmail_api.stop()
app.gmail_api.watch()

if __name__ == '__main__':
    logger.info('Starting App Manually')
    app.run(host='0.0.0.0', port=1337)
