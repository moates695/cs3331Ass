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
from os import chmod, listdir, remove
import re

invalidLogins = {}
attempts = None
allUsernames = []
activeUsernames = []
srs = {}

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
        global allUsernames

        self.clientSocket.send("INPUT~Username: ".encode())
        self.username = self.clientSocket.recv(1024).decode()

        self.clientSocket.send("INPUT~Password: ".encode())
        password = self.clientSocket.recv(1024).decode()
        
        try:
            with open("credentials.txt", "r") as file:
                if self.readFile(file, password):
                    if self.username not in activeUsernames:
                        activeUsernames.append(self.username)
                    return True
                else:
                    return False       
        except IOError as e:
            if e.errno != errno.EPIPE:
                print("Could not open credentials.txt")
                exit()
        except IndexError:
            self.send("ERROR", "Database error: password for user has been lost!")
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
                self.append2Log("userlog.txt", False, clientPort)
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

    def log(self, message, login=False, logout=False, plain=False):
        if login:
            message = "+ " + message
        elif logout:
            message = "- " + message
        else:
            message = "  " + message
        if plain:
            print(message)
        else:
            if self.username == None:
                print(f"{message}: {self.clientAddr[0]} at {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
            else:
                print(f"{message}: {self.username} at {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")

    def body(self):
        while True:
            message = "Enter one of the following commands (BCM, ATU, SRB, SRM, RDM, OUT): "
            if not self.send("INPUT", message):
                break
            cmd = self.clientSocket.recv(1024).decode()
            if len(cmd.split()) == 0 or cmd.split()[0] not in ["BCM","ATU","SRB", "SRM","RDM","OUT","UDP"]:
                self.send("ERROR", "Invalid command!")
                if len(cmd.split()) == 0:
                    self.log(f"No command selected")
                else:
                    self.log(f"Invalid command selected '{cmd}'")
                continue
            elif cmd.split()[0] == "BCM":
                self.log("Command selected 'BCM'")
                self.doBCM(cmd)
            elif cmd.split()[0] == "ATU":
                self.log("Command selected 'ATU'")
                self.doATU(cmd)
            elif cmd.split()[0] == "SRB":
                self.log("Command selected 'SRB'")
                self.doSRB(cmd)
            elif cmd.split()[0] == "SRM":
                self.log("Command selected 'SRM'")
                self.doSRM(cmd)
            elif cmd.split()[0] == "RDM":
                self.log("Command selected 'RDM'")
                self.doRDM(cmd)
            elif cmd.split()[0] == "OUT":
                self.log("Command selected 'OUT'")
                self.doOUT()
                return
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

    def getSeqNum(self, filename, tried=False):
        try:
            seqNum = 1
            with open(filename, "r") as file:
                while True:
                    line = file.readline()
                    if not line:
                        break
                    seqNum += 1  
        except IOError:
            open(filename, "w").close()
            #print(f"Could not open {filename}")
            chmod(filename, 0o777)
            if not tried:
                return self.getSeqNum(filename, true)
            else:
                return -1
        return seqNum
    
    def append2Log(self, filename, tried, *argv):
        seqNum = self.getSeqNum(filename)
        string = datetime.now().strftime("%d %b %Y %H:%M:%S")
        try:
            if filename == "userlog.txt":
                with open(filename, "a") as file:
                    file.write(f"{seqNum}; {string}; {self.username}; {self.clientAddr[0]}; {argv[0]}\n")  
            elif filename == "messagelog.txt":
                with open(filename, "a") as file:
                    file.write(f"{seqNum}; {string}; {self.username}; {argv[0]}\n")
            elif re.match("SR_[0-9]+_messagelog.txt", filename):
                with open(filename, "a") as file:
                    file.write(f"{seqNum}; {string}; {self.username}; {argv[0]}\n")
        except IOError:
            open(filename, "w").close()
            chmod(filename, 0o777)
            if tried:
                exit()
            self.append2Log(filename, True, *argv)
        return seqNum, string

    def doBCM(self, command):
        if len(command.split()) <= 1:
            self.send("LINE", "BCM requires a message body")
            self.log("BCM fail, no message body")
            return      
        seqNum, string = self.append2Log("messagelog.txt", False, command[4:])
        self.send("LINE", f"Broadcast message #{seqNum} at {string}")
        self.log(f"BCM success, #{seqNum}")

    def doATU(self, command):
        if len(command.split()) != 1:
            self.send("LINE", "ATU has no arguments")
            self.log("ATU fail, arguments provided")
            return
        users = []
        try:
            with open("userlog.txt", "r") as file:
                while True:
                    line = file.readline()
                    if not line:
                        break
                    if line.split("; ")[2] == self.username:
                        continue
                    users.append(line)
        except IOError:
            self.log("Cannot open userlog.txt")
            return

        if len(users) == 0:
            self.send("LINE", "No other active users")
        else:
            for user in users:
                split = user[:-1].split("; ")
                self.send("LINE", f"{split[2]} active since {split[1]} at {split[3]} with UDP port {split[4]}")
            self.log("ATU success")

    def doSRB(self, command):
        global srs
        if len(command.split()) == 1:
            self.send("LINE", "SRB requires usernames")
            self.log("SRB fail, no usernames")
            return 
        givenUsernames = command.split()[1:]
        if self.username in givenUsernames:
            self.send("LINE", "SRB cannot contain your username")
            self.log("SRB fail, provided own username")
            return
        givenUsernames.append(self.username)
        if len(set(givenUsernames)) != len(givenUsernames):
            self.send("LINE", "SRB cannot have duplicate usernames")
            self.log("SRB fail, duplicate usernames")
            return

        for idr, room in srs.items():
            if len(room) != len(givenUsernames):
                continue
            for user in  givenUsernames:
                if user not in room:
                    break
            else:
                self.send("LINE", f"SRB room already exists ID: {idr}")
                self.log(f"SRB fail, room already exists ID: {idr}")
                return

        invalid = []
        offline = []
        for username in givenUsernames:
            if username not in allUsernames:
                invalid.append(username)
                continue
            if username not in activeUsernames:
                offline.append(username)
                continue

        if len(invalid) != 0 or len(offline) != 0:
            message = "The following errors occurred:\n"
            for user in invalid:
                message += f"   {user} does not exist\n"
            for user in offline:
                message += f"   {user} is offline\n"
            self.send("LINE", message[:-1])
            self.log("SRB fail, invalid usernames provided")
            return

        idrMax = 0
        for idr in srs.keys():
            if idrMax < idr:
                idrMax = idr
        idrMax += 1
        srs[idrMax] = givenUsernames
        open(f"SR_{idrMax}_messagelog.txt", "w").close()
        message = f"Room ID: {idrMax} created with users: " + " ".join(givenUsernames)
        self.send("LINE", message)
        self.log(f"SRB success, room ID {idrMax} created")

    def doSRM(self, command):
        if len(command.split()) < 3:
            self.send("ERROR", "SRM requires roomID and message")
            self.log("SRM fail, incorrect usage")
            return

        roomId = int(command.split()[1])
        message = " ".join(command.split()[2:])

        if roomId not in srs.keys():
            self.send("LINE", f"Room ID {roomId} does not exist")
            self.log(f"SRM fail, invalid room ID {roomId}")
            return

        if self.username not in srs[roomId]:
            self.send("LINE", f"You are not a member of room ID {roomId}")
            self.log(f"SRM fail, not member of room ID {roomId}")
            return
        
        seqNum, string = self.append2Log(f"SR_{roomId}_messagelog.txt", False, command[4:])
        self.send("LINE", f"SRS message #{seqNum} in room {roomId} at {string}")
        self.log(f"SRM success, message #{seqNum} in room {roomId}")

    def doRDM(self, command):
        if len(command.split()) < 3:
            self.send("ERROR", "RDM requires messageType and timestamp")
            self.log("SRM fail, incorrect usage")
            return

        messageType = command.split()[1]
        timestamp = command.split()[2]

        if messageType not in ["b", "s"]:
            self.send("LINE", "RDM requires messageType 'b' or 's'")
            self.log("SRM fail, incorrect messageType")
            return

    def doOUT(self, sendMessage=True):
        global invalidLogins
        invalidLogins[self.username] = 0
        global activeUsernames
        activeUsernames.remove(self.username)

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

def findUsernames():
    global allUsernames
    try:
        with open("credentials.txt", "r") as file:
            while True:
                line = file.readline()
                if not line:
                    break
                allUsernames.append(line.split()[0])
    except IOError:
        return

def flush():
    open("userlog.txt", "w").close()
    open("messagelog.txt", "w").close()
    filenames = [filename for filename in listdir()]
    for filename in filenames:
        if re.match("SR_[0-9]+_messagelog.txt", filename):
            remove(filename)

def main():
    global attempts

    if len(sys.argv) != 3:
        print("Usage: server.py [serverPort] [attempts]")
        return
    
    fillInvalidLogins()
    findUsernames()
    flush()

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
    print(f"host: {serverHost}")
    print(f"port: {serverPort}")
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
