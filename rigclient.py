#! env python

import argparse
import threading
import time
from queue import Queue

import webview

import radio


def gauge_value_to_s_label(gauge_value):
    float_value = float(gauge_value)

    # values <= 9 are S-meter values, used directly
    if float_value <= 9:
        return f"S{float_value}"
    
    # values > 9 are "S9 + n dBm", where n == 1 is 10dBm, 2 is 20dBm, etc.,
    # so subtract 9 before using the value, and then multiply by 10
    return f"S9+{round(((float_value - 9) * 10))}"

def format_freq(freq_hz):
    freq_len = len(freq_hz) # 7 or 8 depending on band, e.g. length for 7MHz is 7, length for 14MHz is 8

    beginning = ""

    # first 1 or 2 digits, depending on band
    match freq_len:
        case 7:
            beginning = freq_hz[0:1]
        case 8:
            beginning = freq_hz[0:2]

    # next 3 digits
    middle = freq_hz[-6:-3]

    # last 3 digits, but trim trailing zeros 
    end = freq_hz[-3:]
    while end[-1:] == '0':
        end = end[:-1]

    formatted = f"{beginning}.{middle}"

    # only add the remaining digits if not blank
    if len(end) > 0:
        formatted = f"{formatted}.{end}"

    return formatted

def update_mode(js_window, mode):
     cmd = f'acceptMode("{mode}");'
     js_window.run_js(cmd)
     
def update_s_meter(js_window, gauge_value):
    cmd = f'acceptSMeter("{gauge_value}");'
    js_window.run_js(cmd)

    s_label = gauge_value_to_s_label(gauge_value)
    cmd = f'acceptSValue("{s_label}");'
    js_window.run_js(cmd)

def update_freq(js_window, freq):
    formatted = format_freq(freq)
    cmd = f'acceptVFO("{formatted}");'
    js_window.run_js(cmd)


## the python background thread:
## pull data from the response queue (queued in radio.py), and update the HTML UI
def bg_thread(js_window, response_queue):
    while True:
        if not response_queue.empty():
            response = response_queue.get()
            parts = response.split(":")
            command = parts[0]
            value = parts[1]

            match command:
                case "freq":
                    update_freq(js_window, value)

                case "signal_strength":
                    update_s_meter(js_window, value)

                case "mode":
                    update_mode(js_window, value)

                case _:
                    print(f"unhandled: command == {command}")
            
        time.sleep(0)

if __name__ == "__main__":
  
    parser = argparse.ArgumentParser(description="rigclient - a dashboard for your radio using hamlib rigctl(d)")
    parser.add_argument("--host", default="localhost", help="Specify the host computer ip address or name")
    parser.add_argument("--port", default="4532", help="Specify the host computer port")
    args = parser.parse_args()
    # print(f"host = {args.host}, port = {args.port}")

    # TODO: consider using a responsive layout and making the window resizeable
    window = webview.create_window(title="RigClient", url="rigClient.html", width=400, height=350, resizable=True)

    queue = Queue()
    thread = threading.Thread(target=bg_thread, args=(window, queue))
    thread.daemon = True
    thread.start()

    radioThread = threading.Thread(target=radio.request_loop, args=(host:=args.host, port:=args.port, responseQueue:=queue))
    radioThread.daemon = True
    radioThread.start()

    webview.start(debug=False)

