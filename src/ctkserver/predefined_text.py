TEXT = {
    "incomplete_parameters": {"status": "failed", "description": "Incomplete parameters"},
    "no_such_action": {"status": "failed", "description": "No such action"},
    "username_already_in_use": {"status": "failed", "description": "Username already in use"},
    "no-such-user": {"status": "failed", "description": "No such user"},
    "incorrect-password": {"status": "failed", "description": "Incorrect password"},
    "bye-bye": {"status": "success", "description": "Bye-bye"},
    "unexpected_behaviour": {"status": "failed", "description": "Unexpected behaviour"},
    "not_login": {"status": "failed", "description": "Not login"},
    "internal_error": {"status": "failed", "description": "Server internal error"},
    "successfully_registered": {"status": "success", "description": "Successfully registered"},
    "successfully-login": {"status": "success", "description": "Login successfully"},
    "heartbeat": {"status": "success", "description": "Heartbeat"},
    "successfully-updated-info": {"status": "success", "description": "Successfully updated info"},
    "message_sent": {"status": "success", "description": "Message %s sent"},
}


def text(message_id, *kwargs):
    to_return = TEXT[message_id].copy()
    to_return["description"] = to_return["description"] % kwargs
    return to_return
