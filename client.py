"""
Version: Python3.9.2
Author: Marcus Oates, z5257541
"""

import sys
from socket import *
from helper import *

def main():
    if len(sys.argv) != 4:
        print("Usage: server.py [serverHost] [serverPort] [clientPort]")

    serverHost = sys.argv[1]
    serverPort = int(sys.argv[2])
    clientPort = int(sys.argv[3])
    checkPortNumber(clientPort)

if __name__ == "__main__":
    main()