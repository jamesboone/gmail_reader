#!/usr/bin/env python
import re

from jinja2 import evalcontextfilter, Markup
from flask import Flask
import gmail_api


application = Flask(__name__)


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


@application.route('/')
def read_log_file():
    # api = gmail_api.gapi()
    # print 'initialized api, stopping any current watchers'
    # api.stop()
    # print 'finished stop, starting subscribe'
    # subscribe_to_pubsub_topic(api)
    # watch_for_email(api)
    # # app.run(host='0.0.0.0', port=1337,/ debug=True)
    # # app.run(host='0.0.0.0', port=1337)
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


def start():
    #     print 'initializing api'
    #     api = gmail_api.gapi()
    #     print 'initialized api, stopping any current watchers'
    #     api.stop()
    #     print 'finished stop, starting subscribe'
    #     subscribe_to_pubsub_topic(api)
    #     print 'finished subscribe'
    #     watch_for_email(api)
    #     print 'watch_for_email(api) finished'
    #     # app.run(host='0.0.0.0', port=1337,/ debug=True)
    #     # app.run(host='0.0.0.0', port=1337)


    # def subscribe_to_pubsub_topic(instance):
    #     print 'calling subscribe'
    #     instance.sub_to_topic()
    #     print 'finished subscribe'


    # def watch_for_email(instance):
    #     instance.watch()


    # if __name__ == '__main__':
    #     app.run()
    # api = gmail_api.gapi()
    print 'starting'
    gmail_api.gapi()
    print 'initialized api, stopping any current watchers'
    # api.stop()
    # print 'finished stop, starting subscribe'
    # subscribe_to_pubsub_topic(api)
    # watch_for_email(api)
    # # # app.run(host='0.0.0.0', port=1337,/ debug=True)
    # # application.run(host='0.0.0.0', port=1337)