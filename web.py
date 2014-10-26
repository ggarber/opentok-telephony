import os
import logging
import json
import webapp2
import jinja2
from google.appengine.ext import ndb
from opentok import OpenTok

api_key = "20610722"
secret = "fa031480feb1d79ba80e668e94b1a3c17147cbb3"

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Registration(ndb.Model):
    uid = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    session_id = ndb.StringProperty(indexed=False)


class MainPage(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('index.html')
        uid = self.request.get('uid')
        if uid:
            opentok = OpenTok(api_key, secret)
            session = opentok.create_session()

            registration = Registration(parent=ndb.Key('Registration', 'poc'))
            registration.uid = uid
            registration.session_id = str(session.session_id)
            registration.put()

            logging.info('Register uid: ' + uid + ' sessionId: ' + session.session_id)

            self.response.write(template.render({
                'uid': uid,
                'apiKey': api_key,
                'sessionId': session.session_id,
                'token': session.generate_token()
            }))
        else:
            self.response.write(template.render({}))

    def signal(self, session_id, call):
        from google.appengine.api import urlfetch

        url = "https://api.opentok.com/v2/partner/%s/session/%s/signal" % (
            api_key, session_id)
        headers = {
            'User-Agent': 'ggb/test',
            'Content-Type': 'application/json',
            'X-TB-PARTNER-AUTH': api_key + ':' + secret
        }

        response = urlfetch.fetch(url=url,
            payload=json.dumps({ 'type': 'call', 'data': json.dumps(call) }),
            method=urlfetch.POST,
            headers=headers)

        logging.info("signal sent to " + session_id + " status " + str(response.status_code))

    def post(self):
        caller = self.request.get('caller')
        callee = self.request.get('callee')

        registrations = Registration.query(Registration.uid == callee).order(-Registration.date).fetch(5)

        opentok = OpenTok(api_key, secret)
        session = opentok.create_session()
        token = session.generate_token()

        call = {
            'caller': caller,
            'callee': callee,
            'apiKey': api_key,
            'sessionId': session.session_id,
            'token': token
        }
        if not registrations:
            self.abort(404)
            return

        logging.info(str(registrations))
        for registration in registrations:
            self.signal(registration.session_id, call)

        self.response.write(json.dumps(call))

    def options(self):
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = '*'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST'


logging.getLogger().setLevel(logging.DEBUG)
application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)
