from socket import *

ServerName = '127.0.0.1'
ServerPort = 12000

clientSocket = socket(AF_INET,SOCK_DGRAM)
message = input('Input lowercase sentence:')
message = message.encode()
clientSocket.sendto(message, (ServerName,ServerPort))
ModifiedMessage, ServerAddress = clientSocket.recvfrom(2048)
ModifiedMessage = ModifiedMessage.decode()
print(f"{ModifiedMessage}\n")
