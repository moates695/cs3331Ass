#!/usr/bin/env python3
"""
Version: Python 3.9.2
Author: Marcus Oates z5257541
"""

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

# print horizontal breakline
def printBreak():
    print(f"{'='*40}")

# block user login for 10 seconds
class BlockLoginThread(Thread):
    def __init__(self, username, clientHost):
        Thread.__init__(self)
        self.username = username
        self.clientHost = clientHost

    def run(self):
        global invalidLogins
        sleep(10)
        invalidLogins[self.username] = 0
        print(f"  User login unblocked: {self.username}")

class ClientThread(Thread):
    def __init__(self, clientSocket, clientAddr):
        Thread.__init__(self)
        self.clientSocket = clientSocket
        self.clientAddr = clientAddr
        self.clientActive = True
        self.username = None
        self.log("Connection established")

    def run(self):
        if self.login():
            self.body()
        
    def login(self):
        global invalidLogins
        global allUsernames
        # username prompt
        self.clientSocket.send("INPUT~Username: ".encode())
        self.username = self.clientSocket.recv(1024).decode()
        # password prompt
        self.clientSocket.send("INPUT~Password: ".encode())
        password = self.clientSocket.recv(1024).decode()
        
        try:
            with open("credentials.txt", "r") as file:
                if self.readCredentials(file, password):
                    # user is not already logged in
                    if self.username not in activeUsernames:
                        activeUsernames.append(self.username)
                        return True
                    # user already logged in
                    else:
                        self.send("LINE", f"{self.username} is already logged in")
                        self.log(f"Login rejected, {self.username} already logged in")
                        return False
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

    def readCredentials(self, file, password):
        while True:
            line = file.readline()

            # reached EOF, given username does not exist
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
                self.log(f"{self.username} login processed")
                self.send("LINE", "Welcome to Toom!")
                return True
            
            # password is invalid
            else:
                invalidLogins[self.username] += 1
                self.log("Invalid password entered")
                # begin login blocking thread if attempts reached
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

    # print message to server log
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
                print(f"{message}: {self.clientAddr[0]} at {datetime.now().strftime('%H:%M:%S %-d/%m/%Y')}")
            else:
                print(f"{message}: {self.username} at {datetime.now().strftime('%H:%M:%S %-d/%m/%Y')}")

    # prompt loop
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
                self.doOUT(command=cmd)
                return
            else:
                self.log("Command selected 'UDP'")
                self.doUDP(cmd)

    # send message and catch broken pipe
    def send(self, cmd, message):
        fullMessage = cmd + "~" + message + "|"
        try:
            self.clientSocket.send(fullMessage.encode())
        except IOError as e: # structure taken from https://linuxpip.org/broken-pipe-python-error/
            if e.errno == errno.EPIPE:
                self.log("Broken pipe")
                self.doOUT(sendMessage=False)
                exit()
                return False    
        return True      

    # read file and retrieve sequence number
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
            chmod(filename, 0o777)
            if not tried:
                return self.getSeqNum(filename, true)
            else:
                return -1
        return seqNum
    
    # append given message to the given file
    def append2Log(self, filename, tried, *argv):
        seqNum = self.getSeqNum(filename)
        string = datetime.now().strftime("%-d %b %Y %H:%M:%S")
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

    # broadcast message
    def doBCM(self, command):
        # incorrect usage
        if len(command.split()) <= 1:
            self.send("ERROR", "BCM requires a message body")
            self.log("BCM fail, no message body")
            return     

        # append message to log and send response to client
        message = command[4:]
        seqNum, string = self.append2Log("messagelog.txt", False, message)
        self.send("LINE", f"Broadcast message #{seqNum} at {string}")
        self.log(f"BCM success, #{seqNum} '{message}'")

    # download active users
    def doATU(self, command):
        # incorrect usage
        if len(command.split()) != 1:
            self.send("ERROR", "ATU has no arguments")
            self.log("ATU fail, arguments provided")
            return
        
        # retrieve active user data from userlog
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

        # no other active users
        if len(users) == 0:
            self.send("LINE", "No other active users")
            self.log("ATU success, no other active users")
        # other active users exist
        else:
            for user in users:
                split = user[:-1].split("; ")
                message = f"{split[2]} active since {split[1]} at {split[3]} with UDP port {split[4]}"
                self.send("LINE", message)
                self.log(f"")
            self.log("ATU success, active users returned")

    # seperate room building
    def doSRB(self, command):
        global srs
        # incorrect usage
        if len(command.split()) == 1:
            self.send("ERROR", "SRB requires usernames")
            self.log("SRB fail, no usernames")
            return 
        givenUsernames = command.split()[1:]
        # given clients own username
        if self.username in givenUsernames:
            self.send("ERROR", "SRB cannot contain your username")
            self.log("SRB fail, provided own username")
            return
        givenUsernames.append(self.username)
        # duplicate usernames given
        if len(set(givenUsernames)) != len(givenUsernames):
            self.send("ERROR", "SRB cannot have duplicate usernames")
            self.log("SRB fail, duplicate usernames")
            return

        # check if room already exists
        for idr, room in srs.items():
            if len(room) != len(givenUsernames):
                continue
            for user in  givenUsernames:
                if user not in room:
                    break
            # room already exists
            else:
                self.send("LINE", f"SRB room already exists ID: {idr}")
                self.log(f"SRB fail, room already exists ID: {idr}")
                return

        # check if given users exist and are online
        invalid = []
        offline = []
        for username in givenUsernames:
            if username not in allUsernames:
                invalid.append(username)
                continue
            if username not in activeUsernames:
                offline.append(username)
                continue

        # portion of given users may be offline or non-existant
        if len(invalid) != 0 or len(offline) != 0:
            message = "The following errors occurred:\n"
            for user in invalid:
                message += f"   {user} does not exist\n"
            for user in offline:
                message += f"   {user} is offline\n"
            self.send("LINE", message[:-1])
            self.log("SRB fail, invalid usernames provided")
            return

        # create room building
        idrMax = 0
        for idr in srs.keys():
            if idrMax < idr:
                idrMax = idr
        idrMax += 1
        srs[idrMax] = givenUsernames
        open(f"SR_{idrMax}_messagelog.txt", "w").close()
        message = f"Room ID: {idrMax} created with users: " + " ".join(givenUsernames)
        self.send("LINE", message)
        self.log(f"SRB success, room ID {idrMax} created with members {'  '.join(givenUsernames)}")

    # seperate room message
    def doSRM(self, command):
        # incorrect usage
        if len(command.split()) < 3:
            self.send("ERROR", "SRM requires roomID and message")
            self.log("SRM fail, incorrect usage")
            return

        # roomID must be a digit
        if not command.split()[1].isdigit():
            self.send("ERROR", "SRM requires roomID as a digit")
            self.log("SRM fail, incorrect usage")
            return

        roomId = int(command.split()[1])
        message = " ".join(command.split()[2:])

        # no room with roomID exists
        if roomId not in srs.keys():
            self.send("LINE", f"Room ID {roomId} does not exist")
            self.log(f"SRM fail, invalid room ID {roomId}")
            return

        # client is not a member of the room
        if self.username not in srs[roomId]:
            self.send("LINE", f"You are not a member of room ID {roomId}")
            self.log(f"SRM fail, not member of room ID {roomId}")
            return
        
        seqNum, string = self.append2Log(f"SR_{roomId}_messagelog.txt", False, command[6:])
        self.send("LINE", f"SRS message #{seqNum} in room {roomId} at {string}")
        self.log(f"SRM success, message #{seqNum} in room {roomId} '{command[6:]}'")

    # return augmented message format
    def returnFormat(self, line):
        split = line.split("; ")
        num = split[0]
        time = split[1]
        user = split[2]
        message = split[3][:-1]
        return f"#{num}; {user}: {message} at {time}"

    # read messages
    def doRDM(self, command):
        # incorrect usage
        if len(command.split()) < 6:
            self.send("ERROR", "RDM requires messageType and timestamp")
            self.log("RDM fail, incorrect usage")
            return

        messageType = command.split()[1]
        timestampText = " ".join(command.split()[2:])

        if messageType not in ["b", "s"]:
            self.send("ERROR", "RDM requires messageType 'b' or 's'")
            self.log("RDM fail, incorrect messageType")
            return

        timeFormat = "%d %b %Y %H:%M:%S"

        try:
            timestamp = datetime.strptime(timestampText, timeFormat)
        except ValueError:
            self.send("ERROR", "RDM requires timestamp like '1 Jun 2022 21:39:04'")
            self.log("RDM fail, incorrect timestamp format")
            return

        if messageType == "b":
            messages = []
            with open("messagelog.txt", "r") as file:
                while True:
                    line = file.readline()
                    if not line:
                        break
                    messageTime = datetime.strptime(line.split("; ")[1], timeFormat)
                    if messageTime > timestamp:
                        messages.append(self.returnFormat(line))
            
            if len(messages) == 0:
                self.send("LINE", f"No new messages since {timestampText}")
                self.log(f"RDM success for {self.username}")
                return

            self.send("LINE", f"Broadcast messages since {timestampText}:")
            self.log(f"  Sending messages to {self.username}", plain=True)
            for message in messages:
                self.send("LINE", message)
                self.log("  "+message, plain=True)
            self.log(f"RDM success")

        else:
            SRmessages = {}
            for roomId, members in srs.items():
                if self.username not in members:
                    continue
                SRmessages[roomId] = []
                with open(f"SR_{roomId}_messagelog.txt", "r") as file:
                    while True:
                        line = file.readline()
                        if not line:
                            break
                        messageTime = datetime.strptime(line.split("; ")[1], timeFormat)
                        if messageTime > timestamp:
                            SRmessages[roomId].append(self.returnFormat(line))

            for messages in SRmessages.values():
                if len(messages) > 0:
                    break
            else:
                self.send("LINE", f"No new messages since {timestampText}")
                self.log(f"RDM success for {self.username}")
                return

            self.send("LINE", f"Messages in seperate rooms since {timestampText}:")
            self.log(f"  Sending messages to {self.username}", plain=True)
            for roomId, messages in SRmessages.items():
                if len(messages) == 0:
                    continue
                self.send("LINE", f"room-{roomId}:")
                self.log(f"  Sending messages from room-{roomId}", plain=True)
                for message in messages:
                    self.send("LINE", "  " + message)
                    self.log("  "+message, plain=True)
            self.log(f"RDM success")

    # logout
    def doOUT(self, sendMessage=True, command=None):
        # incorrect usage
        if command != None and len(command.split()) != 1:
            self.send("ERROR", "OUT requires no arguments")
            self.log("OUT fail, incorrect usage")
            return

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

    # upload file
    def doUDP(self, command):
        # incorrect usage
        if len(command.split()) != 3:
            self.send("ERROR", "UDP requires username and filename")
            self.log("UDP fail, incorrect usage")
            return

        user = command.split()[1]
        filename = command.split()[2]

        if user == self.username:
            self.send("ERROR", f"UDP username cannot be your own")
            self.log(f"UDP fail, {self.username} supplied own username")
            return

        if user not in allUsernames:
            self.send("LINE", f"{user} does not exist")
            self.log(f"UDP fail, {user} does not exist")
            return

        if user not in activeUsernames:
            self.send("LINE", f"{user} is offline")
            self.log(f"UDP fail, {user} is offline")
            return

        with open("userlog.txt") as file:
            while True:
                line = file.readline()
                if not line:
                    break
                split = line.split("; ")
                if split[2] == user:
                    audienceIP = split[3]
                    audiencePort = split[4]
                elif split[2] == self.username:
                    presenterIP = split[3]
                    presenterPort = split[4]

        self.send("UDP", f"{filename} {audienceIP} {audiencePort} {self.username}")

# initialise invalid logins dictionary
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

# retrieve all usernames from credentials.txt
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

# wipe all server fies
def flush():
    open("userlog.txt", "w").close()
    open("messagelog.txt", "w").close()
    filenames = [filename for filename in listdir()]
    for filename in filenames:
        if re.match("SR_[0-9]+_messagelog.txt", filename):
            remove(filename)

def main():
    global attempts

    # incorrect usage
    if len(sys.argv) != 3:
        print("Usage: server.py [serverPort] [attempts]")
        return
    
    fillInvalidLogins()
    findUsernames()
    flush()

    # retrieve server host, port number and attempts
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

    # create server socket and bind to host IP
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serverSocket.bind(serverAddr)

    printBreak()
    print("SERVER RUNNING")
    print(f"host: {serverHost}")
    print(f"port: {serverPort}")
    printBreak()
    print("Waiting for connection requests...")
    printBreak()

    # listen for client connections, create new threads
    while True:
        serverSocket.listen()
        clientSocket, clientAddr = serverSocket.accept()
        clientThread = ClientThread(clientSocket, clientAddr)
        clientThread.start()

if __name__ == "__main__":
    main()
