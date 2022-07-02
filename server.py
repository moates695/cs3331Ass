"""
Version: Python 3.9.2
Author: Marcus Oates, z5257541
"""

# print(datetime.now().strftime("%-d %B %Y %H:%M:%S"))

import sys
import errno
from socket import *
from datetime import datetime
from threading import Thread, Event
from helper import *
from time import sleep

invalidLogins = {}
attempts = None

def printBreak():
    print(f"{'='*40}")

# send message and catch broken pipe + logout user
def send(clientSocket, clientHost, cmd, message):
    fullMessage = cmd + "~" + message + "|"
    try:
        clientSocket.send(fullMessage.encode())
    except IOError:
        print(f"Broken pipe. User logged out: {clientHost}")
        

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
    def __init__(self, username, clientHost):
        Thread.__init__(self)
        self.username = username
        self.clientHost = clientHost

    def run(self):
        global invalidLogins
        sleep(10)
        invalidLogins[self.username] = 0
        print(f"User login unblocked: {self.clientHost}")

class ClientThread(Thread):
    def __init__(self, clientSocket, clientAddr):
        Thread.__init__(self)
        self.clientSocket = clientSocket
        self.clientAddr = clientAddr
        self.clientActive = True
        print(f"+ Connection established with: {self.clientAddr[0]}")

    def run(self):
        if self.login():
            self.body()
        
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
                        #self.clientSocket.send("LINE~Username does not exist|".encode())
                        message = "Username does not exist"
                        send(self.clientSocket, self.clientAddr, "LINE", message)
                        #print(f"Invalid username provided: {self.clientAddr[0]}")
                        self.log("Invalid username provided")
                        return self.login()
                    # read username does not match given username
                    if line.split()[0] != username:
                        continue
                    # user is currently locked out
                    if invalidLogins[username] == attempts:
                        self.clientSocket.send("LINE~Your account is blocked due to multiple login failures. Please try again later|".encode())
                        print(f"Login attempt while blocked: {self.clientAddr[0]}")
                        self.clientSocket.send("COMMAND~killClient|")
                        #break
                        return False
                    # password is valid
                    if line.split()[1] == password:
                        invalidLogins[username] = 0
                        self.clientSocket.send("COMMAND~sendUDPSocket|".encode())
                        clientPort = int(self.clientSocket.recv(1024).decode())
                        write2UserLog(username, self.clientAddr[0], clientPort)
                        print(f"User login processed: {self.clientAddr[0]}")
                        self.clientSocket.send("LINE~Welcome to Toom!|".encode())
                        #break
                        return True
                    # password is invalid
                    else:
                        invalidLogins[username] += 1
                        print(f"Invalid password entered: {self.clientAddr[0]}")
                        if invalidLogins[username] == attempts:
                            self.clientSocket.send("LINE~Invalid Password. Your account has been blocked. Please try again later|".encode())
                            self.clientSocket.send("COMMAND~killClient".encode())
                            print(f"User login blocked (10s): {self.clientAddr[0]}")
                            blockLogin = BlockLoginThread(username, self.clientAddr[0])
                            blockLogin.start()
                            return False
                        self.clientSocket.send("LINE~Invalid Password. Please try again".encode())
                        return self.login()
                        #break
                        
        except IOError:
            print("Could not open credentials.txt")
            exit()
        except IndexError:
            print("Username has no associated password")

    def log(self, message):
        print(f" {message}: {self.clientAddr[0]} at {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")

    def body(self):
        while True:
            self.clientSocket.send("INPUT~Enter one of the following commands (BCM, ATU, SRB, SRM, RDM, OUT): ".encode())
            cmd = self.clientSocket.recv(1024).decode()
            if len(cmd) == 0 or cmd.split()[0] not in ["BCM","ATU","SRB","SRM","RDM","OUT"]:
                self.clientSocket.send("LINE~Error. Invalid command!".encode())
                continue
            
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
        try:
            clientThread.start()
        except IOError as e: # structure taken from https://linuxpip.org/broken-pipe-python-error/
            if e.errno == errno.EPIPE:
                print(f"Broken ")

if __name__ == "__main__":
    main()
