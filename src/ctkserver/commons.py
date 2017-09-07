# commons.py
# Common operations


# Function name: _schedule
# Description: Schedule a function to run every interval(seconds)
# Return value: no return value
def schedule(func_to_run, interval_second):
    import time
    while True:
        func_to_run()
        time.sleep(interval_second)


# Function name: get_time
# Description: Get timestamp of now
# Return value: timestamp(s)
def get_time():
    import time
    now = int(time.time())
    return now


# Function name: generate_random_code
# Description: Generate ramdom code
# Return value: 80-bit ramdom code
def generate_random_code():
    import random
    seed = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+=-"
    sa = []
    for i in range(80):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    return salt


# Function name: generate_md5
# Description: Generate ramdom code
# Return value: 80-bit ramdom code
def generate_md5(data):
    import hashlib
    hash_md5 = hashlib.md5(data)
    return hash_md5.hexdigest()
