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

BASE_URI = 'https://federation.cyclone-project.eu/auth/realms/master/protocol/openid-connect'
SSO_URL = BASE_URI + '/auth?client_id={0}&redirect_uri={1}&response_type=code'
AUTH_URL = BASE_URI + '/token'
USER_URL = BASE_URI + '/logout'
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


# Server class
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

            # create return object and validate JWT
            result = {'access_token': json_response[u'access_token'],
                      'id_token': json_response[u'id_token'],
                      'dec_access_token': verify_jwt(str(json_response[u'access_token'])),
                      'dec_id_token': verify_jwt(str(json_response[u'id_token'])),
                      'validation': True}

            # answer OK to the user
            self.send_response(200)
            self.end_headers()

            # notify main thread
            self.server.queue.put(result)

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


def start_server(pamh):
    server = CustomTCPServer(('0.0.0.0', 0), CustomRequestHandler, main_queue=queue)
    # create main uri using random generated port
    global PORT
    PORT = server.server_address[1]
    host_ip = socket.gethostname()
    global MY_URI
    MY_URI = 'http://{0}:{1}'.format(host_ip, str(PORT))
    try:
        # spawn the server in another thread
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
    except KeyboardInterrupt:
        print '^C received, shutting down the web server'

    # write the URL to open in the remote shell
    pamh.conversation(pamh.Message(4, 'Browse to ' + MY_URI + ' to login'))
    pamh.conversation(pamh.Message(pamh.PAM_PROMPT_ECHO_ON, '<Press enter to continue>'))

    # block it until there is something in the queue
    access_token = queue.get(True)
    server.shutdown()
    return access_token


def verify_jwt(token):
    with open('/lib/security/key.pem', 'r') as keyFile:
        key = keyFile.read()
    return jwt.decode(token, key, audience=CLIENT_ID)


def get_user_data(access_token):
    user_data_request = urllib2.Request(USER_URL)
    user_data_request.add_header('Authorization', 'Bearer ' + access_token)
    return urllib2.urlopen(user_data_request).read()


def check_whitelist (user_data):
    valid = False
    with open('/lib/security/cyclone_users_list.json') as data_file:
        whitelist = json.load(data_file)

    for email in whitelist['users']:
        if email == user_data['email']:
            valid = True
    return valid


def pam_sm_authenticate(pamh, flags, argv):
    try:
        user = pamh.get_user(None)
    except pamh.exception, e:
        return e.pam_result
    if not user:
        return pamh.PAM_USER_UNKNOWN

    # start the server and get the credentials
    pamh.conversation(pamh.Message(4, 'Starting the server'))
    response = start_server(pamh)

    # check that the validation is positive
    if not response['validation']:
        return pamh.PAM_ERROR
    else:
        pamh.conversation(pamh.Message(4, 'User has been authenticated'))

    # get the user's data
    user_data = get_user_data(response['access_token'])

    # check with whitelist if user is valid
    if check_whitelist(user_data):
        return pamh.PAM_SUCCESS
    else:
        return pamh.PAM_USER_UNKNOWN


def pam_sm_setcred(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_acct_mgmt(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_open_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_close_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_chauthtok(pamh, flags, argv):
    return pamh.PAM_SUCCESS
