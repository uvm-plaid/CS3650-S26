import json


class Authorizer:
    def __init__(self, auth_file_path):
        self.auth_file_path = auth_file_path

    def get_auth_info(self):
        auth_file = open(self.auth_file_path, "r")
        auth_dict = json.load(auth_file)
        auth_file.close()
        return auth_dict

    def is_authorized(self, username, password):
        auth_info = self.get_auth_info()
        return auth_info.get(username, None) == password

    def is_user(self, username):
        auth_info = self.get_auth_info()
        return auth_info.get(username)

    def create_user(self, username, password):
        auth_info = self.get_auth_info()
        auth_info[username] = password

        auth_file = open(self.auth_file_path, "w")
        json.dump(auth_info, auth_file, indent=4, sort_keys=True)
        auth_file.close()
