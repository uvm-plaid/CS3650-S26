from abc import ABCMeta, abstractmethod, abstractproperty
import config


class Response:
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def _message(self):
        pass

    @property
    def message(self):
        message_ = self._message + config.MESSAGE_DELIMINATOR
        print(message_)
        return message_.encode("ascii")


class Ack(Response):
    @property
    def _message(self):
        return "HELLO"


class AuthYes(Response):
    @property
    def _message(self):
        return "AUTHYES"


class AuthNo(Response):
    @property
    def _message(self):
        return "AUTHNO"


class SignIn(Response):
    def __init__(self, user):
        self.user = user

    @property
    def _message(self):
        return "SIGNIN:" + self.user


class SignOff(Response):
    def __init__(self, user):
        self.user = user

    @property
    def _message(self):
        return "SIGNOFF:" + self.user


class UserList(Response):
    def __init__(self, clients):
        self.clients = clients

    @property
    def _message(self):
        return ", ".join([client.username for client in self.clients])


class UserMessage(Response):
    def __init__(self, from_client, message):
        self.from_client = from_client
        self.user_message = message

    @property
    def _message(self):
        return "From:" + self.from_client + ":" + self.user_message


class UserExists(Response):
    @property
    def _message(self):
        return "UNIQNO"


class Info(Response):
    def __init__(self, info):
        self.info = info

    @property
    def _message(self):
        return "# " + self.info

