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

# colour implementation from joeld https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal 
WARNING = '\033[93m'
ENDC = '\033[0m'
chunkSize = 512

class AudienceThread(Thread):
    def __init__(self, audienceSocket):
        Thread.__init__(self)
        self.audienceSocket = audienceSocket
        self.setDaemon(True)

    def run(self):
        dataChunks = []
        while True:
            chunk, presenterAddr = self.audienceSocket.recvfrom(chunkSize)
            try: # try-except structure inspired from https://stackoverflow.com/a/34870210 
                eof = chunk.decode()
            except (UnicodeDecodeError, AttributeError):
                dataChunks.append(chunk)
                continue

            print()
            if eof.split()[0] in [file for file in listdir()]:
                print(f"  Received {eof.split()[0]} from {eof.split()[1]} but it already exists\n"+ "> " + "Enter one of the following commands (BCM, ATU, SRB, SRM, RDM, OUT): ", end="")
                continue

            with open(eof.split()[0], "ab") as file:
                for dataChunk in dataChunks:
                    file.write(dataChunk)
            print(f"  Received {eof.split()[0]} from {eof.split()[1]}\n"+ "> " + "Enter one of the following commands (BCM, ATU, SRB, SRM, RDM, OUT): ", end="")

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
    clientSocket.connect(serverAddr)

    audienceSocket = socket(AF_INET, SOCK_DGRAM)
    audienceSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    audienceSocket.bind((gethostbyname(gethostname()), clientPort))
    audienceThread = AudienceThread(audienceSocket)
    audienceThread.start()

    while True:
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
            elif header == "UDP":
                split = payload.split()
                filename = split[0]
                audienceIP = split[1]
                audiencePort = int(split[2])
                username =split[3]
                audienceAddr = (audienceIP, audiencePort)
                
                if filename not in [file for file in listdir()]:
                    print(f"{WARNING}  UDP fail, file '{filename}' does not exist {ENDC}")
                    continue

                with open(filename, "rb") as file:
                    data = file.read()

                presenterSocket = socket(AF_INET, SOCK_DGRAM)
                presenterSocket.connect(audienceAddr)

                chunkSize = 512
                for i in range(0, len(data), chunkSize):
                    sleep(0.0005)
                    if i + chunkSize >= len(data):
                        chunk = data[i:]
                    else:
                        chunk = data[i:i+chunkSize]
                    presenterSocket.sendto(chunk, audienceAddr)

                presenterSocket.sendto(f"{filename} {username}".encode(), audienceAddr)

                presenterSocket.close()
                print(f"  {filename} has been uploaded")

if __name__ == "__main__":
    main()