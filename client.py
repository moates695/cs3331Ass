"""
Version: Python 3.9.2
Author: Marcus Oates, z5257541
"""

import sys
from socket import *
from helper import *
from threading import Thread

def main():
    if len(sys.argv) != 4:
        print("Usage: server.py [serverHost] [serverPort] [clientPort]")

    serverHost = sys.argv[1]
    serverPort = int(sys.argv[2])
    serverAddr = (serverHost, serverPort)

    clientPort = int(sys.argv[3])
    checkPortNumber(clientPort)

    clientSocket = socket(AF_INET, SOCK_STREAM)
    #clientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    clientSocket.connect(serverAddr)

    while True:
        data = clientSocket.recv(1024).decode()
        header, payload = splitMessage(data)
        
        if header == "INPUT":
            clientSocket.send(input(payload).encode())
        elif header == "COMMAND":
            if payload == "sendUDPSocket":
                clientSocket.send(str(clientPort).encode())
        elif header == "LINE":
            print(payload)

if __name__ == "__main__":
    main()