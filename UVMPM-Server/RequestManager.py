from Request import *
from Client import Client


class RequestManager:
    def __init__(self):
        self.requests = [
            Handshake,
            Authentication,
            ListUsers,
            SendMessage,
            Logout,
            Unknown
        ]

    def get_request(self, client: Client, raw_request: str):
        raw_request = raw_request.strip()

        for request_class in self.requests:
            if request_class.is_of_type(raw_request):
                return request_class(client, raw_request)

        return Unknown(client, None)
