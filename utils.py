import json

def to_json(message, type_msg):
    data = dict()
    data['type'] = type_msg
    data['body'] = message
    return json.dumps(data)


def get_number_bytes_str(message):
    length = len(message)
    length = format(length, '05d')
    return length


class RemoteClient:
    def __init__(self) -> None:
        self.id = ""
        self.nickname = ""
        self.voice_connected = False