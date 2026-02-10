from abc import ABCMeta, abstractmethod
from UVMPMException import InvalidRequestSyntax
from Client import Client


class Request:
    __metaclass__ = ABCMeta

    def __init__(self, client: Client, raw_request: str):
        self.client = client
        self.raw_request = raw_request

    @staticmethod
    @abstractmethod
    def is_of_type(to_match: str):
        pass


class Handshake(Request):
    def __init__(self, client: Client, raw_request: str):
        super().__init__(client, raw_request)

    @staticmethod
    def is_of_type(to_match: str):
        return to_match == "HELLO"


class Authentication(Request):
    def __init__(self, client: Client, raw_request: str):
        super().__init__(client, raw_request)

        split = self.raw_request.split(":")
        if len(split) != 3:
            raise InvalidRequestSyntax(self.raw_request)

        self.username = split[1]
        self.password = split[2]

    @staticmethod
    def is_of_type(to_match: str):
        return to_match.startswith("AUTH:")


class ListUsers(Request):
    def __init__(self, client: Client, raw_request: str):
        super().__init__(client, raw_request)

    @staticmethod
    def is_of_type(to_match: str):
        return to_match == "LIST"


class SendMessage(Request):
    def __init__(self, client: Client, raw_request: str):
        super().__init__(client, raw_request)

        split = self.raw_request.split(":")
        if len(split) != 3:
            raise InvalidRequestSyntax(self.raw_request)

        self.receiving_username = split[1]
        self.message = split[2]

    @staticmethod
    def is_of_type(to_match: str):
        return to_match.startswith("To:")


class Logout(Request):
    def __init__(self, client: Client, raw_request: str):
        super().__init__(client, raw_request)

    @staticmethod
    def is_of_type(to_match: str):
        return to_match == "BYE"


class Unknown(Request):
    def __init__(self, client: Client, raw_request: str):
        super().__init__(client, raw_request)

    @staticmethod
    def is_of_type(to_match: str):
        return True
