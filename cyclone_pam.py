import server


def pam_sm_authenticate(pamh, flags, argv):

    try:
        user = pamh.get_user(None)
    except pamh.exception, e:
        return e.pam_result
    if not user:
        return pamh.PAM_USER_UNKNOWN

    # Start the server and get the credentials
    pamh.conversation(pamh.message(pamh.PAM_TEXT_INFO, 'Starting the server'))
    access_token = server.start_server(pamh)
    pamh.conversation(pamh.message(pamh.PAM_TEXT_INFO, access_token))
    # TODO update to check with whitelist
    return pamh.PAM_SUCCESS


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
