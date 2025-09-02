# radio-interface.py
# receive commands via inbound queue, send to the radio, get response, and put response on outbound queue

import socket
import time
from datetime import datetime

HOST = 'houseserver'  # The server's hostname or IP address
PORT = 4532           # The port used by the server

COMMAND_GET_FREQ = "|f\n"
FREQ_RESPONSE_PREFIX = "get_freq:|Frequency: ";
FREQ_RESPONSE_PREFIX_LEN = len(FREQ_RESPONSE_PREFIX)
FREQ_RESPONSE_SUFFIX = "|RPRT 0"
FREQ_RESPONSE_SUFFIX_LEN = len(FREQ_RESPONSE_SUFFIX)

COMMAND_GET_SIGNAL_STRENGTH = "|l STRENGTH\n"
SIGNAL_STRENGTH_RESPONSE_PREFIX = "get_level: STRENGTH|"
SIGNAL_STRENGTH_RESPONSE_PREFIX_LEN = len(SIGNAL_STRENGTH_RESPONSE_PREFIX)
SIGNAL_STRENGTH_RESPONSE_SUFFIX = "|RPRT 0"
SIGNAL_STRENGTH_RESPONSE_SUFFIX_LEN = len(SIGNAL_STRENGTH_RESPONSE_SUFFIX)

def strengthToSLevel(strengthStr):
    strength = int(strengthStr)
    # under-range (< -54dBm) - return S0
    if strength < -54:
      print(f'strength under-range: strength {strength} is < -54, returning 0 (s0)');
      return 0;

    # over-range: > 60dBm, return S9+60
    if strength > 60:
        print(f'signal strength over-range: strength {strength} is > 60dBm, returning 15 (s9+60)');
        return 15 # don't go beyond full scale at S9+60    

    # S0 (-54dBm) to S9 (0dBm) - scaled from 0 to 9 for the gauge
    if strength <= 0 :
      return (strength + 54) / 6

    # S9+ : 1dBm (S9+1), up to 60dBm (S9+60), scaled to 10 to 15 for the gauge
    if strength > 0:
      return (strength / 10) + 9 


def parseResponse(response):
    if response.startswith(FREQ_RESPONSE_PREFIX):
        val = response[FREQ_RESPONSE_PREFIX_LEN:] # e.g. 14074840|RPRT 0
        val = val[:FREQ_RESPONSE_SUFFIX_LEN]
        return f"freq:{val}"
    
    if response.startswith(SIGNAL_STRENGTH_RESPONSE_PREFIX):
        val = response[SIGNAL_STRENGTH_RESPONSE_PREFIX_LEN:]  # e.g. '21|RPRT 0'
        dBm = val[:-(SIGNAL_STRENGTH_RESPONSE_SUFFIX_LEN+1)] # e.g. '21'
        # todo - convert from dBm to s-units
        sLevel = strengthToSLevel(dBm)
        return f"signal_strength:{round(sLevel,1)}" # sLevel is 0-15 for the gauge, dBm is the s-number label

    print(f"Unhandled response: {response}")
    return ""

def sendRequest(socket, command, responseQueue):
    socket.sendall(command.encode())
    data = socket.recv(1024)
    rawResponse = data.decode()
    # print(f"raw: {rawResponse}")
    responseValue = parseResponse(rawResponse)
    if len(responseValue) > 0:
        responseQueue.put(responseValue)

def data_loop(responseQueue):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        while True:
            sendRequest(s, COMMAND_GET_FREQ, responseQueue)
            sendRequest(s, COMMAND_GET_SIGNAL_STRENGTH, responseQueue)
            time.sleep(1)
