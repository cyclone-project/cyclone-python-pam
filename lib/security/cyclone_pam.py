#!/usr/bin/python
import SimpleHTTPServer
import SocketServer
import socket
import threading
import urlparse
import urllib2
import urllib
import json
import random
from datetime import datetime
import Queue
from jose import jwt

BASE_URI = 'https://federation.cyclone-project.eu/auth/realms/master/protocol/openid-connect'
SSO_URL = BASE_URI + '/auth?client_id={0}&redirect_uri={1}&response_type=code'
AUTH_URL = BASE_URI + '/token'
USER_URL = BASE_URI + '/userinfo'
CALLBACK_URI = '/sso_callback'
CLIENT_ID = 'test'

keep_running = True
queue = Queue.Queue()


def generate_redirect_uri(uri):
    """
    Generates a full redirect URL given the port and endpoint
    :param uri:
    :return: string with formatted URI
    """
    redirect_uri = '{0}{2}'.format(MY_URI, str(PORT), uri)
    return redirect_uri


class CustomTCPServer(SocketServer.TCPServer):
    """
    Custom TCP server that enables reuse of address and queuing to save data
    """
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, main_queue=None):
        self.queue = main_queue
        self.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=True)


# Server class
class CustomRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        """
        Handles HTTP GET requests to the server
        It checks for the redirect/callback URL, or the root URL
        Otherwise returns a 404 error
        :return: The data is returned to the main thread through the queue
        """
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

        # root url redirect to login page
        elif parsed_url.path == '/':
            print 'Redirecting to SSO login page'
            url = SSO_URL.format(CLIENT_ID, generate_redirect_uri(CALLBACK_URI))
            self.send_response(301)
            self.send_header('Location', url)
            self.end_headers()

        else:
            self.send_error(404, 'File Not Found: %s' % self.path)


def generate_random_port(argv):
    """
    Generates a random port number according to the configured available ports in
    :return: port number (0, which means random port if no file found or some problem generating a random number)
    """
    config_file = argv[1]
    # try to open the json file
    try:
        with open(config_file) as data_file:
            config = json.load(data_file)
    except IOError:
        return 0

    # check the parameter exists in the JSON file
    if 'ports' not in config:
        return 0

    # check if there are items
    if len(config['ports']) == 0:
        return 0

    ports = []
    # loop through the items and generate the available ports array
    for item in config['ports']:
        if isinstance(item, list):
            if (len(item) == 2) & (item[0] < item[1]):
                ports = ports + range(item[0], item[1])
        else:
            ports.append(item)

    # return a random item in the array
    random.seed(datetime.now())
    return random.choice(ports)


def start_server(pamh, argv):
    """
    Starts a server in a new thread listening in a random number
    It waits until the server thread sends back the results before stopping it
    :param pamh: PAM handler to write messages back to the user
    :return: data obtained form the OIDC server
    """
    port = generate_random_port(argv)
    try:
        server = CustomTCPServer(('0.0.0.0', port), CustomRequestHandler, main_queue=queue)
    except socket.error:
        pamh.conversation(pamh.Message(pamh.PAM_PROMPT_ECHO_ON, 'Can\'t start browser in port ' + str(port) + '. Trying again...'))
        return None

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
    data = queue.get(True)
    server.shutdown()
    return data


def verify_jwt(token):
    """
    Verifies that a JWT is valid with the public key
    :param token: JWT token to verify
    :return: decoded JWT
    """
    with open('/lib/security/key.pem', 'r') as keyFile:
        key = keyFile.read()
    return jwt.decode(token, key, audience=CLIENT_ID)


def get_user_data(access_token):
    """
    Requests the user data from the user endpoint of OIDC
    :param access_token: authentication token to authenticate against the server
    :return: object with user data
    """
    user_data_request = urllib2.Request(USER_URL)
    user_data_request.add_header('Authorization', 'Bearer ' + access_token)
    response = urllib2.urlopen(user_data_request).read()
    return json.loads(response)


def check_whitelist (user_data, user, pamh):
    """
    Check if the specified user is in the white list of allowed users
    :param user: name of the user to login to
    :param pamh: pamh handler to write back to the user
    :param user_data: user data fetched from the institution's user data endpoint
    :return: pamh flag
    """
    if user == 'root':
        path = '/root/.edugain'
    else:
        path = '/home/' + user + '/.edugain'

    try:
        with open(path) as data_file:
            whitelist = json.load(data_file)
    except IOError:
        pamh.conversation(pamh.Message(pamh.PAM_PROMPT_ECHO_ON, 'ERROR: Unknown user ' + user))
        return pamh.PAM_USER_UNKNOWN

    if 'email' not in user_data:
        pamh.conversation(pamh.Message(pamh.PAM_PROMPT_ECHO_ON, 'ERROR: Non existing mail parameter in the data provided by your institution'))
        return pamh.PAM_AUTHINFO_UNAVAIL

    for email in whitelist['users']:
        if email == str(user_data['email']):
            return pamh.PAM_SUCCESS

    pamh.conversation(pamh.Message(pamh.PAM_PROMPT_ECHO_ON, 'ERROR: Your user cannot login as' + user))
    return pamh.PAM_USER_UNKNOWN


def pam_sm_authenticate(pamh, flags, argv):
    try:
        user = pamh.get_user(None)
    except pamh.exception, e:
        return e.pam_result
    if not user:
        return pamh.PAM_USER_UNKNOWN

    # start the server and get the credentials
    pamh.conversation(pamh.Message(pamh.PAM_TEXT_INFO, 'Starting the server'))
    response = start_server(pamh, argv)
    if response is None:
        return pamh.PAM_ERROR

    # check that the validation is positive
    if not response['validation']:
        return pamh.PAM_ERROR
    else:
        pamh.conversation(pamh.Message(pamh.PAM_TEXT_INFO, 'User has been authenticated'))

    # get the user's data
    user_data = get_user_data(response['access_token'])

    # check with whitelist if user is valid
    return check_whitelist(user_data, user, pamh)


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
