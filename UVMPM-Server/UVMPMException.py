
class InvalidRequestSyntax(Exception):
    def __init__(self, request):
        message = "Invalid request syntax: " + request
        super().__init__(message)
