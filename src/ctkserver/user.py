from ctkserver.commons import get_time, generate_random_code


# Function name: logged_in
# Description: Check if a user is (precisely) logged in
# Return value: True/False
def logged_in(LOGGEDIN_USERS, username):
    if username in LOGGEDIN_USERS and get_time() - LOGGEDIN_USERS[username]["time"] <= 60:
        return True
    else:
        return False


# Function name: log_in
# Description: Log in a new user and return its ID
# Return value: user ID
def log_in(LOGGEDIN_USERS, username):
    id = generate_random_code()
    while id in LOGGEDIN_USERS:
        id = generate_random_code()
    LOGGEDIN_USERS[username] = {
        "id": id,
        "time": get_time(),
    }
    return id


# Function name: heartbeat
# Description: Log new time in LOGGED_IN_USERS
# Return value: no return value
def heartbeat(LOGGEDIN_USERS, username):
    LOGGEDIN_USERS[username]["time"] = get_time()
