from socket import *

ServerPort = 12000

ServerSocket = socket(AF_INET,SOCK_DGRAM)
ServerSocket.bind(("",ServerPort))
print("The server is ready to receive")
while True:
    Message, clientAddress = ServerSocket.recvfrom(2048)
    #print(clientAddress)
    #print(Message)
    Message = Message.decode()
    ModifiedMessage = Message.upper()
    ModifiedMessage = ModifiedMessage.encode()
    ServerSocket.sendto(ModifiedMessage, clientAddress)