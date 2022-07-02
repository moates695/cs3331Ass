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
from time import sleep

invalidLogins = {}
attempts = None

def printBreak():
    print(f"{'='*40}")

def write2UserLog(username, clientIP, clientPort):
    try:
        seqNum = 1
        with open("userlog.txt", "r") as file:
            while True:
                line = file.readline()
                if not line:
                    break
                seqNum += 1  
    except IOError:
        pass
    
    try:
        with open("userlog.txt", "a") as file:
            string = datetime.now().strftime("%-d %B %Y %H:%M:%S")
            file.write(f"{seqNum}; {string}; {username}; {clientIP}; {clientPort}")  
    except IOError:
        print("Could not open userlog.txt")
        exit()

class BlockLoginThread(Thread):
    def __init__(self, username):
        Thread.__init__(self)
        self.username = username

    def run(self):
        global invalidLogins
        sleep(10)
        invalidLogins[self.username] = 0

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
        global invalidLogins
        self.clientSocket.send("INPUT~Username: ".encode())
        username = self.clientSocket.recv(1024).decode()
        #print(username)
        self.clientSocket.send("INPUT~Password: ".encode())
        password = self.clientSocket.recv(1024).decode()
        #print(password)
        try:
            with open("credentials.txt", "r") as file:
                while True:
                    line = file.readline()
                    # username does not exist
                    if not line:
                        self.clientSocket.send("LINE~Username does not exist".encode())
                        break
                    # username does not match given username
                    if line.split()[0] != username:
                        continue
                    # user is currently locked out
                    if invalidLogins[username] == attempts:
                        self.clientSocket.send("LINE~Your account is blocked due to multiple login failures. Please try again later".encode())
                        break
                    # password is valid
                    if line.split()[1] == password:
                        invalidLogins[username] = 0
                        self.clientSocket.send("LINE~Welcome to Toom!".encode())
                        self.clientSocket.send("COMMAND~sendUDPSocket".encode())
                        clientPort = int(self.clientSocket.recv(1024).decode())
                        write2UserLog(username, self.clientAddr[0], clientPort)
                        break
                    # password is invalid
                    else:
                        invalidLogins[username] += 1
                        if invalidLogins[username] == attempts:
                            self.clientSocket.send("LINE~Invalid Password. Your account has been blocked. Please try again later".encode())
                            blockLogin = BlockLoginThread(username)
                            blockLogin.start()
                        break
        except IOError:
            print("Could not open credentials.txt")
            exit()
        except IndexError:
            print("Username has no associated password")

def fillInvalidLogins():
    global invalidLogins
    try:
        with open("credentials.txt", "r") as file:
            while True:
                line = file.readline()
                if not line:
                    break
                invalidLogins[line.split()[0]] = 0
    except IOError:
        print("Could not open credentials.txt")
        exit()

def main():
    global attempts
    if len(sys.argv) != 3:
        print("Usage: server.py [serverPort] [attempts]")
    
    fillInvalidLogins()

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
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
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
        clientThread.start()

if __name__ == "__main__":
    main()