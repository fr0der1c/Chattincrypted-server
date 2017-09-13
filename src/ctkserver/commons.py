# commons.py
# Description: Common operations
import struct


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
# Description: Generate random code
# Return value: 80-bit random code
def generate_md5(data):
    import hashlib
    hash_md5 = hashlib.md5(data.encode(encoding='utf-8'))
    return hash_md5.hexdigest()


# Function name: send_msg
# Description: Prefix each message with a 4-byte length (network byte order) and send it.
#              See https://stackoverflow.com/questions/17667903/python-socket-receive-large-amount-of-data
#              for more information.
# Return value: no return value
def send_msg(sock, msg):
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)


# Function name: recv_all
# Description  : Helper function to recv n bytes or return None if EOF is hit
# Return value : bytes data
def recv_all(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


# Function name: recv_msg
# Description  : Helper function to recv n bytes or return None if EOF is hit
# Return value : bytes data
def recv_msg(sock):
    # Read message length and unpack it into an integer
    raw_msg_len = recv_all(sock, 4)
    if not raw_msg_len:
        return None
    msg_len = struct.unpack('>I', raw_msg_len)[0]
    # Read the message data if msg_len < 21MB
    if msg_len < 1024 * 1024 * 21:
        return recv_all(sock, msg_len)
    else:
        return None
