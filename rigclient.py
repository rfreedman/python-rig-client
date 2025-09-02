#! env python3

import webview
import asyncio
import threading
import time
from datetime import datetime
import random
import re  
import radio
from queue import Queue

def getMode(): 
     # TODO: use the HamLib rigctl api to get the mode from the radio
     return 'USB'

def gaugeValueToSLabel(gaugeValue):
    floatValue = float(gaugeValue)
    if floatValue <= 9:
        return f"S{floatValue}"
    
    return f"S9+{round(((floatValue - 9) * 10))}"

def updateSMeter(jsWindow, gaugeValue):
    cmd = f'acceptSMeter("{gaugeValue}");'
    jsWindow.run_js(cmd) 

    sLabel = gaugeValueToSLabel(gaugeValue)
    cmd = f'acceptSValue("{sLabel}");' 
    jsWindow.run_js(cmd)  

def formatFreq(freqHz):
    freq_len = len(freqHz) # 7 or 8 depending on band, e.g. length for 7MHz is 7, length for 14MHz is 8

    beginning = ""

    # first 1 or 2 digits, depending on band
    match freq_len:
        case 7:
            beginning = freqHz[0:1] 
        case 8:
            beginning = freqHz[0:2]

    # next 3 digits
    middle = freqHz[-6:-3]

    # last 3 digits, but trim trailing zeros 
    end = freqHz[-3:]
    while end[-1:] == '0':
        end = end[:-1]

    formatted = f"{beginning}.{middle}"

    # only add the remaining digits if not blank
    if len(end) > 0:
        formatted = f"{formatted}.{end}"

    return formatted

def updateFreq(jsWindow, freq):
    formatted = formatFreq(freq)
    cmd = f'acceptVFO("{formatted}");'
    jsWindow.run_js(cmd) 


## the python background thread:
## talk to hamlib to get the radio data and send the result to the webview, once every 1/2 second
# TODO: when actually using rigCtl to talk to the radio, it will be async, so these will just be requests,
# and the responses will be sent to the UI when they arrive. Probably use queues.
def bg_thread(jsWindow, queue):
    while(True):  
        if not queue.empty():
            response = queue.get()
            parts = response.split(":")
            command = parts[0]
            value = parts[1]

            match command:
                case "freq":
                    updateFreq(jsWindow, parts[1])

                case "signal_strength":
                    slevel = parts[1]
                    updateSMeter(jsWindow, slevel)

                case _:
                    print(f"unhandled: parts[0] == {parts[0]}")
            
        time.sleep(0.5)

# TODO: consider using a responsive layout and making the window resizeable
window = webview.create_window(title="RigClient", url="rigClient.html", width=400, height=350, resizable=False);

queue = Queue()
thread = threading.Thread(target=bg_thread, args=(window, queue))
thread.daemon = True
thread.start()

radioThread = threading.Thread(target=radio.data_loop, args=(queue, ))
radioThread.daemon = True
radioThread.start()

webview.start(debug=False)
