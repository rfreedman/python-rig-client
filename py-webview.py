#! env python3

import webview
import asyncio
import threading
import time
from datetime import datetime
import random
import re  

def getMode(): 
     # TODO: use the HamLib rigctl api to get the mode from the radio
     return 'USB'

def getFreq():
    # TODO: use the HamLib rigctl api to get the VFO frequency from the radio
    freqHz = 7427910 # frequency in Hz

    # convert to MHz
    freqMHz = freqHz / 1000000

    # format to text, such that, e.g. 742791Hz becomes '7.427.910' instead of '7.42791'
    freqStr = f"{freqMHz}0"
    return freqStr[:-3] + "." + freqStr[-3:]

  
def getSignalStrengthFromRadio(): # returns signal strength in dB, generally in the range of -54dB (S0) to 60db (S9+60)
        # TODO: use the HamLib rigctl api to get the signal strength from the radio
        return random.uniform(-54, 60)  

def getSignalStrength():
        sLevelDb = getSignalStrengthFromRadio()
        sLevel = strengthToSLevel(sLevelDb)
        return round(sLevel, 1)

'''
Convert signal strength from dBm relative to S9 to range of 0-15 for the (linear) S-meter gauge
according to https://hamlib-developer.narkive.com/UNmwDxca/icom-rig-level-strength:

* RIG_LEVEL_STRENGTH: val is an integer, representing the S Meter
* level in dB relative to S9, according to the ideal S Meter scale.
*
* The ideal S Meter scale is as follows: 
* S0 =   -54, 
* S1 =   -48, 
* S2 =   -42, 
* S3 =   -36,
* S4 =   -30, 
* S5 =   -24, 
* S6 =   -18, 
* S7 =   -12, 
* S8 =    -6, 
* S9 =     0, 
+ S9+10 = 10, 
* S9+20 = 20,
* S9+30 = 30, 
* S9+40 = 40, 
* S9+50 = 50,
* S9+60 = 60. 
'''
def strengthToSLevel(strength):
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


def updateSMeter(jsWindow):
    val = getSignalStrength();
    cmd = f'acceptSMeter("{val}");'
    jsWindow.run_js(cmd)    

def updateFreq(jsWindow):
    val = getFreq()
    cmd = f'acceptVFO("{val}");'
    jsWindow.run_js(cmd) 

def updateMode(jsWindow):
    val = getMode()
    cmd = f'acceptMode("{val}")'
    jsWindow.run_js(cmd) 

## the python background thread:
## talk to hamlib to get the radio data and send the result to the webview, once every 1/2 second
# TODO: when actually using rigCtl to talk to the radio, it will be async, so these will just be requests,
# and the responses will be sent to the UI when they arrive. Probably use queues.
def bg_thread(jsWindow):
    while(True):  
        updateSMeter(jsWindow)
        updateFreq(jsWindow)
        updateMode(jsWindow)
        time.sleep(0.5)

# TODO: consider using a responsive layout and making the window resizeable
window = webview.create_window(title="RigClient", url="rigClient.html", width=400, height=350, resizable=False);


thread = threading.Thread(target=bg_thread, args=(window,))
thread.daemon = True
thread.start()

webview.start(debug=True)
