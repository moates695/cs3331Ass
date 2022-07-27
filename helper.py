"""
Version: Python 3.9.2
Author: Marcus Oates, z5257541
"""

# port number must be >= 1024
def checkPortNumber(port):
    if port < 1024:
        print("Error: port number must be 1024 or greater")
        exit()

# split message into Header and Payload
# with '~' delimeter
def splitMessage(message):
    try:
        header = message.split("~")[0]
        payload = " ".join(message.split("~")[1:])
        return header, payload
    except IndexError:
        print(f"Error: Message invalid format: {message}")
        exit()