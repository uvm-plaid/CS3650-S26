from Client import Client
from Authorizer import Authorizer
from typing import Dict
import socket
import select
from Response import Response, SignOff
from RequestManager import RequestManager
import time
from threading import Timer
from UVMPMException import InvalidRequestSyntax


class ClientManager:
    TIMEOUT = 120  # seconds

    def __init__(self):
        self.authorizer = Authorizer("auth_info.json")

        self.request_manager = RequestManager()

        self.sockets: Dict[int, socket.socket] = {}  # fileno : sock

        self.clients: Dict[int, Client] = {}  # fileno : client
        self.authorized_clients: Dict[str, Client] = {}  # username : client

        self.buffered_data: Dict[int, str] = {}  # fileno : data

        self.poller = select.poll()

        self.remove_idle_clients_forever()

    def client_exists(self, sock: socket.socket):
        return sock.fileno() in self.clients

    def create_client(self, sock: socket.socket):
        if self.client_exists(sock):
            return

        client = Client(sock)

        self.clients[sock.fileno()] = client
        self.sockets[sock.fileno()] = sock
        self.poller.register(sock, select.POLLIN)

        print(str(client), "connected.")

    def login_client(self, client: Client, username: str):
        self.authorized_clients[username] = client
        client.set_authorized(username)

        print(str(client), "authorized.")

    def remove_client(self, client: Client):
        self.clients.pop(client.sock.fileno(), None)
        if client.username:
            self.authorized_clients.pop(client.username, None)
        self.sockets.pop(client.sock.fileno(), None)
        self.buffered_data.pop(client.sock.fileno(), None)
        if client.sock.fileno() > -1:
            self.poller.unregister(client.sock.fileno())

        client.sock.close()

        print(str(client), "disconnected.")

    def broadcast(self, response: Response):
        for client in self.authorized_clients.values():
            client.send_response(response)

    def remove_idle_clients_forever(self):
        now = time.time()
        for client in list(self.clients.values()):
            if now - client.last_interaction_time > ClientManager.TIMEOUT:
                self.remove_client(client)
                self.broadcast(SignOff(client.username))
                print("removing", str(client), "due to inactivity")

        Timer(10, self.remove_idle_clients_forever).start()

    def add_data(self, fileno, data):
        if fileno not in self.buffered_data:
            self.buffered_data[fileno] = ""
        self.buffered_data[fileno] += data

    def pop_buffered_requests(self, fileno: int):
        raw_messages = self.buffered_data.get(fileno)
        if not raw_messages:
            return []

        client = self.clients.get(fileno)

        split = raw_messages.split("\n")
        raw_messages = split[:-1]
        requests = []
        for raw_message in raw_messages:
            try:
                requests.append(self.request_manager.get_request(client, raw_message))
            except InvalidRequestSyntax:
                self.remove_client(client)
                return []

        self.buffered_data[fileno] = split[-1]

        return requests
