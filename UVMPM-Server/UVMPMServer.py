from ClientManager import ClientManager
from RequestHandler import RequestHandler
import socket
import select
import config


class UVMPMServer:
    def __init__(self, host="0.0.0.0", port=1145):
        self.host = host
        self.port = port

        self.client_manager = ClientManager()

        self.request_handler = RequestHandler(self.client_manager)

        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_socket.bind((self.host, self.port))

        self.client_manager.poller.register(self.listening_socket, select.POLLIN)

    def run(self):
        self.listening_socket.listen()
        print("Listening on port", self.port)

        self.client_manager.sockets[self.listening_socket.fileno()] = self.listening_socket

        while True:
            for fd, event in self.client_manager.poller.poll():
                sock = self.client_manager.sockets.get(fd, None)
                if not sock:
                    continue

                if sock is self.listening_socket:
                    sock, address = self.listening_socket.accept()
                    sock.setblocking(False)
                    self.client_manager.create_client(sock)

                elif event & select.POLLIN:
                    try:
                        incoming_data = sock.recv(config.BUFFER_SIZE)
                    except Exception:
                        # connection reset, connection refused, etc
                        continue

                    try:
                        decoded_data = incoming_data.decode("ascii")
                    except Exception:
                        # unable to convert to ascii
                        continue

                    if len(incoming_data) == 0:
                        self.client_manager.poller.modify(sock, select.POLLHUP)
                        continue

                    self.client_manager.add_data(sock.fileno(), decoded_data)

                    requests = self.client_manager.pop_buffered_requests(sock.fileno())
                    for request in requests:
                        self.request_handler.handle(request)

                elif event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
                    client = self.client_manager.clients.get(sock.fileno())
                    self.client_manager.remove_client(client)
