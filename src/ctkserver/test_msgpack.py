import msgpack

dict = {
    "action": "register",
    "parameters": {
        "username": "test",
        "password": "pwd",
    }
}
print(msgpack.dumps(dict))
print(len(msgpack.dumps(dict)))
print(msgpack.dumps(dict, use_bin_type=True))
