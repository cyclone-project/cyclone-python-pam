#!/usr/bin/python
from oic.oic import Client
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from oic import rndstr
from oic.oic.message import AuthorizationResponse
from oic.oic.message import RegistrationResponse
from configobj import ConfigObj
import requests
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse
import Queue
import random
import threading
import socket

oidc_client = None
server = None
config = None

# Default Constants
DEFAULT_GLOBAL_CONFIG_PATH = '/etc/cyclone/cyclone.conf'
DEFAULT_CALLBACK_PATH = 'auth/oidc'
DEFAULT_PORTS = ['8080', '8081', '5000-6000']
DEFAULT_AUTHENTICATION_HTML = '/etc/cyclone/authenticated.html'
DEFAULT_LOG_PATH = '/var/log/cyclone.log'
# DEBUG
# DEFAULT_GLOBAL_CONFIG_PATH = '../../../etc/cyclone/cyclone.conf'


class CycloneOIDC:
    """
    Represents an object that saves all the session data and needed functions to handle OIDC calls
    """
    def __init__(self, oidc_host, realm, client_id, client_secret, redirect_uri):
        """
        Initializes CycloneOIDC with basic configuration parameters
        :param oidc_host: the host (including protocol) to where to connect
        :param realm: realm being used in Keycloak
        :param client_id: Client ID credential
        :param client_secret: Client Secret credential
        :param redirect_uri: local URI to where to redirect the user after authentication and post the credentials
        """
        # Generate config
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.client_id = client_id
        self.realm = realm
        self.oidc_host = oidc_host

        # Generate some static variables
        self.oidc_info_url = '{:s}/auth/realms/{:s}/'.format(self.oidc_host, self.realm)
        self.state = rndstr()
        self.nonce = rndstr()
        self.client = Client(client_authn_method=CLIENT_AUTHN_METHOD)

        # Variable where we will save the user's info and authorization status
        self.user_info = None
        self.authenticated = False
        self.redirected = False

    def generate_login_url(self):
        """
        Configures pyOIDC with exposed OIDC configuration in Keycloak and generates a login URL 
        :return: string containing the login URL
        """
        # Fetch OIDC configuration
        self.redirected = True

        self.client.provider_config(self.oidc_info_url)

        # Add client credentials
        info = {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        client_reg = RegistrationResponse(**info)
        self.client.store_registration_info(client_reg)

        args = {
            "client_id": self.client.client_id,
            "response_type": "code",
            "scope": ["openid"],
            "nonce": self.nonce,
            "redirect_uri": self.redirect_uri,
            "state": self.state
        }

        auth_req = self.client.construct_AuthorizationRequest(request_args=args)
        login_url = auth_req.request(self.client.authorization_endpoint)

        return login_url

    def parse_authentication_response(self, query_string):
        """
        Processes OIDC answer to generate an access token and fetch the user's data,
        which is then stored in this same class
        :param query_string: urlencoded query string recieved from the OIDC server
        :return: returns boolean indicating the success
        """

        if not self.redirected:
            return

        # Decode the answer and validate the sessions and nonce
        auth_response = self.client.parse_response(AuthorizationResponse,
                                                   info=query_string,
                                                   sformat="urlencoded")

        if auth_response['state'] != self.state:
            return False

        if "id_token" in auth_response and auth_response["id_token"]["nonce"] != self.nonce:
            return False

        # Request an access token an use it to require the user's information
        args = {
            "code": auth_response["code"]
        }

        self.client.do_access_token_request(state=auth_response["state"],
                                            request_args=args,
                                            authn_method="client_secret_basic")

        self.authenticated = True
        self.user_info = self.client.do_user_info_request(state=auth_response["state"])

        return True

    def get_user_info(self):
        """
        :return: returns the user_info in case it got fetched. None otherwise
        """
        return self.user_info

    def authenticated(self):
        """
        :return: returns if the user has already been authenticated or not
        """
        return self.authenticated


class CycloneServer(BaseHTTPRequestHandler):
    """
    BaseHTTPRequestHandler implementation to create a simple and fast HTTP server to handle redirections and callbacks
    """
    def index(self):
        """
        / path of the server
        :return: Returns redirection to the login_url of OIDC
        """
        global oidc_client
        login_url = oidc_client.generate_login_url()
        self.send_response(303)
        self.send_header('Location', login_url)
        self.end_headers()
        return

    def auth(self, query):
        """
        /auth path of the server
        Processes the callback from the OIDC server with the validated credentials
        :param query: code and state of the authentication
        :return: Returns always a successful authentication answer, 
        and sends a message to another thread asking the server to be stopped
        """
        successful = False
        global oidc_client
        if not oidc_client.authenticated:
            successful = oidc_client.parse_authentication_response(query)
        if successful:
            global queue
            queue.put(True)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        f = open(DEFAULT_AUTHENTICATION_HTML, 'rb')
        self.wfile.write(f.read())
        f.close()

    def do_GET(self):
        """
        GET entry point of the server. Redirects to the proper path
        :return: an HTTP answer or a 404 in case of a wrong path received
        """
        query = urlparse(self.path)
        if query.path == '/{:s}'.format(DEFAULT_CALLBACK_PATH):
            self.auth(query.query)
        elif query.path == '/':
            self.index()
        else:
            self.send_response(404)


def setup_oidc(conf, port):
    """
    Creates an OIDC client object based on the loaded configuration
    :param conf: loaded configuration
    :param port: chosen port in where to run the server
    """
    global oidc_client
    oidc_client = CycloneOIDC(
        oidc_host=conf['OIDC_HOST'],
        realm=conf['REALM'],
        client_id=conf['CLIENT_ID'],
        client_secret=conf['CLIENT_SECRET'],
        redirect_uri='http://{:s}:{:d}/{:s}'.format(conf['HOSTNAME'], port, DEFAULT_CALLBACK_PATH)
    )


queue = Queue.Queue()


def run_server(port, host, pamh):
    """
    Runs the server in its own thread and stops it when received the queue notification of authentication finished
    :param port: chosen port in where to run the server
    :param host: host in where the client user can locate this server
    :param pamh: PAM handle from python_pam module
    """
    try:
        # Create a web server and define the handler to manage the
        # incoming request
        if pamh is not None:
            pamh.conversation(pamh.Message(4, 'Browse to http://{:s}:{:d}'' to login'.format(host, port)))
            pamh.conversation(pamh.Message(pamh.PAM_PROMPT_ECHO_ON, '<Press enter to continue>'))
        else:
            print ('Started server in http://{:s}:{:d}'.format(host, port))

        global server
        server = HTTPServer(('0.0.0.0', port), CycloneServer)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        queue.get(True)
        server.shutdown()
    except KeyboardInterrupt:
        server.socket.close()


def get_local_username(pamh):
    """
    Returns the local user name wanting to authenticate
    :param pamh: PAM handle from python_pam module
    :return: local username or empty string if not found
    """
    try:
        user = pamh.get_user(None)
    except:
        user = ''

    return user


def generate_random_port(conf_ports):
    """
    Generates a random available port given the port configuration
    :param conf_ports: configuration string containing the different possible ports
    :return: an available port number
    """
    ports = []
    for item in conf_ports:
        items = item.split('-')
        if len(items) == 2:
            ports = ports + range(int(items[0]), int(items[1]))
        elif len(items) == 1:
            ports.append(item)

    chosen_port = random.choice(ports)

    while not is_port_available(chosen_port):
        chosen_port = random.choice(ports)

    return chosen_port


def is_port_available(port):
    """
    Checks if a given port is available trying to open it with a socket
    :param port: port to test
    :return: returns boolean with the port availability
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        available = True
    except socket.error:
        available = False
    s.close()
    return available


def load_config(global_config_path):
    """
    Loads the configuration from a given path
    :param global_config_path: path from where to load the configuration
    :return: object containing all the loaded configuration
    """
    global config
    config = ConfigObj(global_config_path)

    if 'PORTS' not in config:
        config['PORTS'] = DEFAULT_PORTS

    if 'CUSTOM_AUTHENTICATION_HTML' not in config:
        config['CUSTOM_AUTHENTICATION_HTML'] = DEFAULT_AUTHENTICATION_HTML

    if 'CUSTOM_CALLBACK_PATH' not in config:
        config['CUSTOM_CALLBACK_PATH'] = DEFAULT_CALLBACK_PATH

    # Load the FQDN from openstack
    if 'HOSTNAME_OPENSTACK' not in config:
        try:
            config['HOSTNAME'] = requests.get(config['HOSTNAME_OPENSTACK']).text
        except:
            pass

    # In case openstack fails and hostname is empty, fetch it from the server itself
    if 'HOSTNAME_OPENSTACK' not in config and 'HOSTNAME' not in config:
        config['HOSTNAME'] = socket.getfqdn()

    return config


def validate_authorization(local_username):
    """
    Checks if the given local username's mail matches with the one provided by OIDC authentication service
    :param local_username: user's local machine username
    :return: boolean indicating the success of the authorization
    """
    if local_username == 'root':
        path = '/root/.cyclone'
    else:
        path = '/home/' + local_username + '/.cyclone'

    # DEBUG
    # path = '../../.cyclone'

    global oidc_client
    user_mail = oidc_client.get_user_info()[u'mail']
    user_email = oidc_client.get_user_info()[u'email']
    conf_emails = ConfigObj(path)['EMAIL']

    return user_email in conf_emails or user_mail in conf_emails


def log(log_info):
    log_file = open(DEFAULT_LOG_PATH, 'w')
    log_file.writelines(log_info + '\n')
    log_file.close()


def pam_sm_authenticate(pamh, flags, argv):
    """
    pam_python implementation of the pam_sm_authenticate method of PAM modules
    This function handles and returns the authentication of a PAM module
    :param pamh: PAM handle from python_pam module
    :param flags: configuration flags given to the module
    :param argv: arguments given to the PAM module in pam.d configuration
    :return: flag indicating the success or error of the authentication
    """
    try:

        local_username = get_local_username(pamh)
        # DEBUG
        # local_username = 'sturgelose'
        if local_username == '':
            return pamh.PAM_USER_UNKNOWN

        conf = load_config(DEFAULT_GLOBAL_CONFIG_PATH)
        port = generate_random_port(conf['PORTS'])
        setup_oidc(conf, port)
        run_server(port, conf['HOSTNAME'], pamh)
        validated = validate_authorization(local_username)

        if pamh is not None:
            if validated:
                return pamh.PAM_SUCCESS
            else:
                return pamh.PAM_USER_UNKNOWN
    except Exception as e:
        print ('Exception found:', e)
        log(str(e))


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


if __name__ == "__main__":
    pam_sm_authenticate(None, None, None)
