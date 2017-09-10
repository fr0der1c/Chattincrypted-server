import struct
import time

import msgpack

with open('test_image.png', 'rb') as f:
    data_json = {
        "action": "send-message",
        "parameters": {
            "type": "file",
            "message": "f.read()",
            "receiver": "lavender",
            "time1": "time",
            "time": int(round(time.time() * 1000)),
        }
    }

packed = msgpack.packb(data_json, use_bin_type=True)
msg = struct.pack('>I', len(packed)) + packed
print(msgpack.unpackb(packed, encoding='utf-8'))
print(len(packed))
