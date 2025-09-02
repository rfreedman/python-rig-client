# radio-interface.py
# receive commands via inbound queue, send to the radio, get response, and put response on outbound queue

import socket
import time
from datetime import datetime

HOST = 'houseserver'  # The server's hostname or IP address
PORT = 4532           # The port used by the server

COMMAND_STATUS_PREFIX = "|RPRT "
COMMAND_SUCCESS = "|RPRT 0"

COMMAND_GET_FREQ = "|f\n"
FREQ_RESPONSE_PREFIX = "get_freq:|Frequency: "

COMMAND_GET_SIGNAL_STRENGTH = "|l STRENGTH\n"
SIGNAL_STRENGTH_RESPONSE_PREFIX = "get_level: STRENGTH|"



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

def parseResponseValue(str, prefix, suffix):
    val = str[len(prefix):]
    val = val[:-(len(suffix) + 1)]
    return val    

def response_code_from_status(status):
    return status[len(COMMAND_STATUS_PREFIX):]

def parseResponse(response):
    response_status = response[-(len(COMMAND_SUCCESS)+1):]
    if(not response_status[-1].isdigit()): # trim trailing carriage return and or linefeed
        response_status = response_status[:-1]

    if response.startswith(FREQ_RESPONSE_PREFIX):
        if response_status == COMMAND_SUCCESS:
            # e.g. response == "get_freq:|Frequency: 14074100|RPRT 0"
            val = parseResponseValue(response, FREQ_RESPONSE_PREFIX, COMMAND_SUCCESS)
            return f"freq:{val}"
        else:
            response_code = response_code_from_status(response_status)
            print(f"bad get_freq command response code: {response_code}")
            return ""
        
    
    if response.startswith(SIGNAL_STRENGTH_RESPONSE_PREFIX):
        if response_status == COMMAND_SUCCESS:
            # e.g. response == "get_level: STRENGTH|-29|RPRT 0"
            dBm = parseResponseValue(response, SIGNAL_STRENGTH_RESPONSE_PREFIX, COMMAND_SUCCESS)
            sLevel = strengthToSLevel(dBm)
            return f"signal_strength:{round(sLevel,1)}" # sLevel is 0-15 for the gauge
        else:
            response_code = response_code_from_status(response_status)
            print(f"bad get_signal_strength command response code: {response_code}")
            return f"signal_strength:0"

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
