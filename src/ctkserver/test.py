import msgpack
list1=["Hello","你好"]
print(msgpack.dumps(list1))
print(msgpack.loads(msgpack.dumps(list1)))