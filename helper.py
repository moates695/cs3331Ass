"""
Version: Python3.9.2
Author: Marcus Oates, z5257541
"""

# port number must be >= 1024
def checkPortNumber(port):
    if port < 1024:
        print("Error: port number must be 1024 or greater")
        exit()