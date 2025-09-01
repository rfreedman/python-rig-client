# radio-interface.py
# receive commands via inbound queue, send to the radio, get response, and put response on outbound queue

import socket
import time
from datetime import datetime

HOST = 'houseserver'  # The server's hostname or IP address
PORT = 4532           # The port used by the server

def sendVFORequest():
    print("sendVFORequest")
    # try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        while True:
            command_to_send = "|f"
            s.sendall(command_to_send.encode())
            data = s.recv(1024)
            print(f"{datetime.now().time()}: {data.decode()}")
            time.sleep(0.5)
    #except:
    #    pass
