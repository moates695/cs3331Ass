"""
Version: Python 3.9.2
Author: Marcus Oates, z5257541
"""

# print(datetime.now().strftime("%-d %B %Y %H:%M:%S"))

import sys
from socket import *
from datetime import datetime
from threading import Thread
from helper import *

def printBreak():
    print(f"{'='*40}")

class ClientThread(Thread):
    def __init__(self, clientSocket, clientAddr):
        Thread.__init__(self)
        self.clientSocket = clientSocket
        self.clientAddr = clientAddr
        self.clientActive = True
        print(f"Connection established with: {self.clientAddr}")

    def run(self):
        self.login()

    def login(self):
        self.clientSocket.send("Username: ".encode())
        username = self.clientSocket.recv(1024).decode()
        print(username)
        self.clientSocket.send("Password: ".encode())
        password = self.clientSocket.recv(1024).decode()
        print(password)

def main():
    if len(sys.argv) != 3:
        print("Usage: server.py [serverPort] [attempts]")
    
    serverHost = gethostbyname(gethostname())
    serverPort = int(sys.argv[1])
    checkPortNumber(serverPort)
    serverAddr = (serverHost, serverPort)
    try:
        attempts = int(sys.argv[2])
        if not 1 <= attempts <= 5:
            print("Error: attempt limit must be between 1 and 5")
            exit()
    except ValueError:
        print("Error: attempt limit must be integer value")

    serverSocket = socket(AF_INET, SOCK_STREAM)
    #serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    #serverSocket.setblocking(False)
    serverSocket.bind(serverAddr)

    printBreak()
    print("SERVER RUNNING")
    print(f"port: {serverPort}")
    print(f"host: {serverHost}")
    printBreak()
    print("Waiting for connection requests...")
    printBreak()

    while True:
        serverSocket.listen()
        clientSocket, clientAddr = serverSocket.accept()
        clientThread = ClientThread(clientSocket, clientAddr)
        clientThread.run()

if __name__ == "__main__":
    main()