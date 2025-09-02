# radio-interface.py
# receive commands via inbound queue, send to the radio, get response, and put response on outbound queue

import socket
import time
from datetime import datetime

HOST = 'houseserver'  # The server's hostname or IP address
PORT = 4532           # The port used by the server

COMMAND_STATUS_PREFIX = "|RPRT "
COMMAND_SUCCESS = "|RPRT 0"

COMMAND_GET_FREQ = "|\\get_freq\n"
FREQ_RESPONSE_PREFIX = "get_freq:|Frequency: "

COMMAND_GET_SIGNAL_STRENGTH = "|\\get_level STRENGTH\n"
SIGNAL_STRENGTH_RESPONSE_PREFIX = "get_level: STRENGTH|"

COMMAND_GET_MODE = "|\\get_mode\n"
MODE_RESPONSE_PREFIX = "get_mode:|Mode: "

client_socket = None

def connect_to_server():
    global client_socket

    while True:
        try:
            client_socket = None
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"attempting connection to {HOST}:{PORT} on socket {client_socket}")
            client_socket.connect((HOST, PORT))
            print("Successfully connected to the server.")
            return client_socket
        except ConnectionRefusedError:
            print("Connection refused. Retrying in 5 seconds...")
            if client_socket:
                client_socket.close()
            time.sleep(5)
        except OSError as e:
            if client_socket:
                client_socket.close()
            print(f"Error connecting: {e}. Retrying in 5 seconds...")
            time.sleep(5)

connect_to_server()


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
    # trim off the prefix and the suffix
    val = str[len(prefix):]
    val = val[:-(len(suffix) + 1)]
    return val    

def response_code_from_status(status):
    return status[len(COMMAND_STATUS_PREFIX):]

def parseResponse(response):
    # handle socket disconnect
    if response == "":
        return ""

    response_status = response[-(len(COMMAND_SUCCESS)+1):]
    if(not response_status[-1].isdigit()): # trim trailing carriage return and or linefeed
        response_status = response_status[:-1]

    if response.startswith(MODE_RESPONSE_PREFIX):
        if response_status == COMMAND_SUCCESS:
            # e.g. response == "get_mode:|Mode: USB|Passband: 2400|RPRT 0"
            val = parseResponseValue(response, MODE_RESPONSE_PREFIX, COMMAND_SUCCESS)
            
            # val includes passband info, e.g. "USB|Passband: 2400", so pick off just the mode
            parts = val.split('|')
            val = parts[0]
            return f"mode:{val}"


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

# send a single command to the radio via the rigctl api, and queue the response
def sendRequest(command, responseQueue):
    global client_socket

    try:
        client_socket.sendall(command.encode())
        data = client_socket.recv(1024)
        rawResponse = data.decode()
        responseValue = parseResponse(rawResponse)
        if len(responseValue) > 0:
            responseQueue.put(responseValue)
    except BrokenPipeError:
        print("socket connection broken. Attempting to reconnect...")
        if client_socket:
            client_socket.close()
            client_socket = None
        connect_to_server()

    except Exception as e:
        print(f"Error in sendRequest: {e}")
        if client_socket:
            client_socket.close()
            client_socket = None
        connect_to_server()
        pass

# query the radio via the rigctl api, and put responses on the queue to be dequeued in rigclient.py (bg_thread)
def request_loop(responseQueue):
    while True:
        sendRequest(COMMAND_GET_MODE, responseQueue)
        sendRequest(COMMAND_GET_FREQ, responseQueue)
        sendRequest(COMMAND_GET_SIGNAL_STRENGTH, responseQueue)
        time.sleep(0.5)
