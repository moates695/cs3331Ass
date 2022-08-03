"""
Version: Python 3.9.2
Author: Marcus Oates z5257541
"""

import sys
from socket import *
from helper import *
from threading import Thread
from os import listdir
from time import sleep
#import tqdm

# colour implementation from joeld https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal 
WARNING = '\033[93m'
ENDC = '\033[0m'

class ClientThread(Thread):
    def __init__(self, clientSocket, clientPort):
        Thread.__init__(self)
        self.clientSocket = clientSocket
        self.clientPort = clientPort

    def run(self):
        while True:
            data = self.clientSocket.recv(1024).decode()
            for d in data.split('|'):
                header, payload = splitMessage(d)
                
                if header == "INPUT":
                    self.clientSocket.send(input("> " + payload).encode())
                elif header == "COMMAND":
                    if payload == "killClient":
                        exit()
                    elif payload == "sendUDPSocket":
                        self.clientSocket.send(str(self.clientPort).encode())
                elif header == "LINE":
                    print("  " + payload)
                elif header == "ERROR":
                    print(f"{WARNING}  ERROR: " + payload +f"{ENDC}")

class UDPThread(Thread):
    def __init__(self, clientSocket, clientAddr):
        Thread.__init__(self)
        self.clientSocket = clientSocket
        self.clientAddr = clientAddr
        self.clientActive = True
        self.username = None
        print(f"+ Connection established with: {self.clientAddr[0]}")

    def run(self):
        pass

def main():
    if len(sys.argv) != 4:
        print("Usage: server.py [serverHost] [serverPort] [clientPort]")
        return

    serverHost = sys.argv[1]
    serverPort = int(sys.argv[2])
    serverAddr = (serverHost, serverPort)

    clientPort = int(sys.argv[3])
    checkPortNumber(clientPort)

    clientSocket = socket(AF_INET, SOCK_STREAM)
    #clientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    clientSocket.connect(serverAddr)
    clientThread = ClientThread(clientSocket, clientPort)
    clientThread.start()

    UDPSocket = socket(AF_INET, SOCK_DGRAM)
    UDPSocket.bind((gethostbyname(gethostname()), clientPort))
    udpThread = UDPThread(UDPSocket)

    """ while True:
        data = clientSocket.recv(1024).decode()
        for d in data.split('|'):
            header, payload = splitMessage(d)
            
            if header == "INPUT":
                clientSocket.send(input("> " + payload).encode())
            elif header == "COMMAND":
                if payload == "killClient":
                    exit()
                elif payload == "sendUDPSocket":
                    clientSocket.send(str(clientPort).encode())
            elif header == "LINE":
                print("  " + payload)
            elif header == "ERROR":
                print(f"{WARNING}  ERROR: " + payload +f"{ENDC}")
            elif header == "UDP_CHECKFILE":


                role = payload.split()[0]
                filename = payload.split()[1]
                audienceIP = payload.split()[2]
                #print(audienceIP)
                audiencePort = int(payload.split()[3])
                audienceAddr = (audienceIP, audiencePort)
                #print(audiencePort)
                presenterIP = payload.split()[4]
                #print(presenterIP)
                presenterPort = int(payload.split()[5])
                #print(presenterPort)
                if role == "presenter":
                    sleep(0.05)
                    if filename not in [file for file in listdir()]:
                        print(f"{WARNING}  UDP fail, file {filename} does not exist {ENDC}")
                        continue
                    with open(filename, "rb") as file:
                        data = file.read()
                    
                    #presenterAddr = (presenterIP, presenterPort)
                    presenterSocket = socket(AF_INET, SOCK_DGRAM)
                    presenterSocket.connect(audienceAddr)

                    chunkSize = 512
                    for i in range(0, len(data), chunkSize):
                        sleep(0.001)
                        #print(f"sending chunk")
                        if i + chunkSize > len(data):
                            chunk = data[i:]
                        else:
                            chunk = data[i:i+chunkSize]
                        presenterSocket.sendto(chunk, audienceAddr)

                else:
                    audienceSocket = socket(AF_INET, SOCK_DGRAM)
                    audienceSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                    audienceSocket.bind(audienceAddr)
                    print("Audience ready to receive data")
                    while True:
                        dataSegment, presenterAddr = audienceSocket.recvfrom(512)
                        data += dataSegment """

if __name__ == "__main__":
    main()