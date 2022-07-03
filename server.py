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
        self.username = None
        print(f"+ Connection established with: {self.clientAddr[0]}")

    def run(self):
        if self.login():
            self.body()
        
    def login(self):
        global invalidLogins
        
        self.clientSocket.send("INPUT~Username: ".encode())
        self.username = self.clientSocket.recv(1024).decode()

        self.clientSocket.send("INPUT~Password: ".encode())
        password = self.clientSocket.recv(1024).decode()
        
        try:
            with open("credentials.txt", "r") as file:
                    return self.readFile(file, password)       
        except IOError as e:
            if e.errno != errno.EPIPE:
                print("Could not open credentials.txt")
                exit()
        except IndexError:
            self.send("LINE", "Database error: password for user has been lost!")
            self.log("Username has no associated password")
            return self.login()

    def readFile(self, file, password):
        while True:
            line = file.readline()

            # username does not exist
            if not line:
                self.send("LINE", "Username does not exist")
                self.log("Invalid username provided")
                return self.login()
            
            # read username does not match given username
            if line.split()[0] != self.username:
                continue
            
            # user is currently locked out
            if invalidLogins[self.username] == attempts:
                message = "Your account is blocked due to multiple login failures. Please try again later"
                self.send("LINE", message)
                self.log("Login attempt while blocked")
                self.send("COMMAND", "killClient")
                return False
            
            # password is valid
            if line.split()[1] == password:
                invalidLogins[self.username] = 0
                self.send("COMMAND", "sendUDPSocket")
                clientPort = int(self.clientSocket.recv(1024).decode())
                self.append2UserLog(self.username, clientPort)
                self.log("User login processed")
                self.send("LINE", "Welcome to Toom!")
                return True
            
            # password is invalid
            else:
                invalidLogins[self.username] += 1
                self.log("Invalid password entered")
                
                if invalidLogins[self.username] == attempts:
                    message = "Invalid Password. Your account has been blocked. Please try again later"
                    self.send("LINE", message)
                    self.send("COMMAND", "killClient")
                    self.log("User login blocked (10s)")
                    
                    blockLogin = BlockLoginThread(self.username, self.clientAddr[0])
                    blockLogin.start()
                    return False
                
                self.send("LINE", "Invalid Password. Please try again")
                return self.login()

    def log(self, message, login=False, logout=False):
        if login:
            message = "+ " + message
        elif logout:
            message = "- " + message
        else:
            message = "  " + message
        print(f"{message}: {self.clientAddr[0]} at {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")

    def body(self):
        while True:
            message = "Enter one of the following commands (BCM, ATU, SRB, SRM, RDM, OUT): "
            if not self.send("INPUT", message):
                break
            cmd = self.clientSocket.recv(1024).decode()
            if len(cmd.split()) == 0 or cmd.split()[0] not in ["BCM","ATU","SRB", "SRM","RDM","OUT","UDP"]:
                self.send("LINE", "Error. Invalid command!")
                if len(cmd.split()) == 0:
                    self.log(f"No command selected")
                else:
                    self.log(f"Invalid command selected '{cmd}'")
                continue
            elif cmd.split()[0] == "BCM":
                self.log("BCM command selected")
                self.doBCM()
            elif cmd.split()[0] == "ATU":
                self.log("ATU command selected")
                self.doATU()
            elif cmd.split()[0] == "SRB":
                self.log("SRB command selected")
                self.doSRB()
            elif cmd.split()[0] == "SRM":
                self.log("SRM command selected")
                self.doSRM()
            elif cmd.split()[0] == "RDM":
                self.log("RDM command selected")
                self.doRDM()
            elif cmd.split()[0] == "OUT":
                self.log("OUT command selected")
                self.doOUT()
            else:
                self.doUDP()

    # send message and catch broken pipe
    def send(self, cmd, message):
        fullMessage = cmd + "~" + message + "|"
        try:
            self.clientSocket.send(fullMessage.encode())
        except IOError as e: # structure taken from https://linuxpip.org/broken-pipe-python-error/
            if e.errno == errno.EPIPE:
                self.log("Broken pipe")
                self.doOUT(False)
                exit()
                return False    
        return True      

    # append message to userlog.txt
    def append2UserLog(self, username, clientPort):
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
                file.write(f"{seqNum}; {string}; {username}; {self.clientAddr[0]}; {clientPort}\n")  
        except IOError:
            print("Could not open userlog.txt")
            exit()
    
    def doBCM(self):
        pass

    def doATU(self):
        pass

    def doSRB(self):
        pass

    def doSRM(self):
        pass

    def doRDM(self):
        pass

    def doOUT(self, sendMessage=True):
        entrys = []
        shift = False
        try:
            with open("userlog.txt", "r") as file:
                while True:
                    line = file.readline()
                    if not line:
                        break
                    if line.split("; ")[2] == self.username:
                        shift = True
                        continue
                    if not shift:
                        entrys.append(line)
                    else:   
                        entrys.append(str(int(line[0])-1)+line[1:])            
            with open("userlog.txt", "w") as file:
                for entry in entrys:
                    file.write(entry)
        except IOError as e:
            if e.errno != errno.EPIPE:
                print("Could not open userlog.txt")
                exit()
        except IndexError:
            print("Details stored incorrectly in userlog.txt")
            exit()
        if sendMessage:
            self.send("LINE", f"Bye {self.username}!")
            self.send("COMMAND", "killClient")
        self.log("User logged out", logout=True)

    def doUDP(self):
        pass

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
