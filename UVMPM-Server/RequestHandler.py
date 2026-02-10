import Request
import Response
from ClientManager import ClientManager
import Client


class RequestHandler:
    def __init__(self, client_manager: ClientManager):
        self.client_manager = client_manager

        self.request_function_map = {
            Request.Handshake: self._on_handshake,
            Request.Authentication: self._on_authentication,
            Request.ListUsers: self._on_list_users,
            Request.SendMessage: self._on_send_message,
            Request.Logout: self._on_logout,
            Request.Unknown: self._on_unknown
        }

    def handle(self, request: Request):
        print(str(request.client), request.raw_request)
        request.client.reset_interaction_timer()
        self.request_function_map.get(request.__class__)(request)

    def _on_handshake(self, request: Request.Handshake):
        request.client.set_greeted()
        request.client.send_response(Response.Ack())

    def _on_authentication(self, request: Request.Authentication):
        if request.client.state == Client.State.NOT_GREETED:
            request.client.send_response(Response.AuthNo())
            return

        existing_user = self.client_manager.authorized_clients.get(request.username)
        if existing_user:
            request.client.send_response(Response.UserExists())
            return

        if self.client_manager.authorizer.is_authorized(request.username, request.password):
            self.client_manager.login_client(request.client, request.username)
            request.client.send_response(Response.AuthYes())
            self.client_manager.broadcast(Response.SignIn(request.client.username))
        else:
            request.client.send_response(Response.AuthNo())

    def _on_list_users(self, request: Request.ListUsers):
        if request.client.state != Client.State.AUTHORIZED:
            self.client_manager.remove_client(request.client)
            return

        request.client.send_response(Response.UserList(self.client_manager.authorized_clients.values()))

    def _on_send_message(self, request: Request.SendMessage):
        if request.client.state != Client.State.AUTHORIZED:
            self.client_manager.remove_client(request.client)
            return

        send_to = self.client_manager.authorized_clients.get(request.receiving_username, None)
        if not send_to:
            return

        send_to.send_response(Response.UserMessage(request.client.username, request.message))

    def _on_logout(self, request: Request.Logout):
        self.client_manager.remove_client(request.client)
        if request.client.username:
            self.client_manager.broadcast(Response.SignOff(request.client.username))

    def _on_unknown(self, request: Request.Unknown):
        self.client_manager.remove_client(request.client)
        if request.client.username:
            self.client_manager.broadcast(Response.SignOff(request.client.username))
