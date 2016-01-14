#!/usr/bin/python
import SimpleHTTPServer
import SocketServer
import socket
import threading
import urlparse
import urllib2
import urllib
import json
import Queue
from jose import jwt

BASE_URI = 'https://federation.cyclone-project.eu'
SSO_URL = BASE_URI + '/auth/realms/master/protocol/openid-connect/auth?client_id={0}&redirect_uri={1}&response_type=code'
AUTH_URL = BASE_URI + '/auth/realms/master/protocol/openid-connect/token'
CALLBACK_URI = '/sso_callback'
CLIENT_ID = 'test'

keep_running = True
queue = Queue.Queue()


def generate_redirect_uri(uri):
    redirect_uri = '{0}{2}'.format(MY_URI, str(PORT), uri)
    return redirect_uri


class CustomTCPServer(SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, main_queue=None):
        self.queue = main_queue
        self.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=True)


class CustomRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse.urlparse(self.path)

        # if it's a callback to CALLBACK_URI
        if parsed_url.path == CALLBACK_URI:
            self.send_response(200)
            self.wfile.write("Code validated!")
            self.end_headers()

            print 'SSO login callback received'
            # check we have the code parameter
            code = urlparse.parse_qs(parsed_url.query)['code'][0]

            # do a POST call with the code to get the id
            data = urllib.urlencode({'grant_type': 'authorization_code',
                                     'code': code,
                                     'redirect_uri': generate_redirect_uri(CALLBACK_URI),
                                     'client_id': CLIENT_ID})
            request = urllib2.Request(AUTH_URL, data)
            request.add_header('Content-Type', 'application/x-www-form-urlencoded')
            f = urllib2.urlopen(request)

            # process the info received
            response = f.read()
            json_response = json.loads(response)
            # TODO verify the JWT token
            global access_token
            access_token = jwt.get_unverified_claims(str(json_response[u'access_token']))

            # answer OK to the user
            self.send_response(200)
            self.end_headers()

            # notify main thread
            self.server.queue.put(access_token)

        elif parsed_url.path == CALLBACK_URI:
            print 'AUTH validation callback received'
            # answer OK to the user
            self.send_response(200)
            self.end_headers()

        # root url redirect to login page
        elif parsed_url.path == '/':
            print 'Redirecting to SSO login page'
            url = SSO_URL.format(CLIENT_ID, generate_redirect_uri(CALLBACK_URI))
            self.send_response(301)
            self.send_header('Location', url)
            self.end_headers()

        else:
            self.send_error(404, 'File Not Found: %s' % self.path)


server = CustomTCPServer(('0.0.0.0', 0), CustomRequestHandler, main_queue=queue)
# create main uri using random generated port
PORT = server.server_address[1]
host_ip = socket.gethostbyname(socket.gethostname())
MY_URI = 'http://{0}:{1}'.format(host_ip, str(PORT))
try:
    # spawn the server in another thread
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    print MY_URI
except KeyboardInterrupt:
    print '^C received, shutting down the web server'

# block it until there is something in the queue
queue.get(True)
server.shutdown()
print access_token
