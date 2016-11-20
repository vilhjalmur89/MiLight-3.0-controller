# -*- coding: utf-8 -*-
"""
Created on Sun Sep 11 22:19:38 2016

@author: vilhjalmur
"""

import socket
import time
import sys
import json

info = {}
with open('info.txt', 'r') as f:
    info = json.loads(f.readline())
IPADDR = info['ip']
PORTNUM = int(info['port'])
print IPADDR, PORTNUM

# Hex values found by sniffing UDP packages
init_msg = '200000001602623ad5eda301ae082d466141a7f6dcaf83c8000064'
resp_msg = '3000000003'
end_msg = '8000000011'
on  = 'd80031000007030100000001003d'
off = 'd80031000007030200000001003e'
white = 'd800310000070305000000010041'
night_light = 'd800310000070306000000000041'

colorToRGB = {'red'     : 28,
              'orange'  : 47,
              'yellow'  : 64,
              'green'   : 98,
              'cyan'    : 127,
              'blue'    : 198,
              'magenta' : 233
              }

def toHexStr(x):
    ''' Returns a string of two chars, representing the a byte in hex'''
    assert 0 <= x <= 255
    s = hex(x)[2:]
    if len(s) < 2:
        s = '0' + s
    return s

def sumHexStr(s):
    ''' Returns the sum of s modulus 256
        s is a string where s[i:i+2] are two chars representing a byte in hex'''
    assert len(s) % 2 == 0
    total = 0
    for i in range(0, len(s), 2):
        total += int('0x' + s[i:i+2], 16)
    return toHexStr(total % 256)
    
def getCheckSum(s):
    ''' Returns the sum modulus 256 of the last 11 bytes of s'''
    return sumHexStr(s[-22:])
#    return toHexStr((58 + 4*val) % 256)
    
def turnOn():
    sendAction(on)
    
def turnOff():
    sendAction(off)

def setWhite():
    sendAction(white)

def setNightLight():
    sendAction(night_light)
    
def setBrightness(brightness):
    brightness = int(brightness)
    assertRange(brightness, 0, 100, 'brightness')
    
    val = toHexStr(brightness)
    action = 'd8003100000702' + val + '0000000100'
    action += getCheckSum(action)
#    print action
    sendAction(action)
    
def setRGB(hue):
    rgb = int(hue)
    assertRange(rgb, 0, 255, 'hue')
    val = toHexStr(rgb)
    action = 'd8003100000701' + (val*4) + '0100'
    action += getCheckSum(action)
    sendAction(action)

def setColorByName(color):
    ''' Must be called with  a color from colorToRGB'''
    color = color.lower().strip()
    if color == 'white':
        setWhite()
    elif color in colorToRGB:
        setRGB(colorToRGB[color])
    else:
        raise(Exception('color must be one of {}'.format(colorToRGB.keys())))
        
def setSunrise(init_val, end_val, total_time):
    ''' Must be called with inital_brightness end_brightness total_time'''
    sunrise(int(init_val), int(end_val), int(total_time))
        
def sunrise(init_val, end_val, total_time=None, sleep_time=None, step_size=1):
    ''' Increases the brightness from init_val to end_val
        If total_time is not set, then sleep_time must be set
        To get a "sunse"', set step_size to be negative and end_val > init_val
    '''    
    if not (end_val >= init_val or step_size < 0):
        raise(Exception('end_val must be greater than init_val unless step_size is negative'))
    if not (total_time is not None or sleep_time is not None):        
        raise(Exception('Either total_time or sleep_time must be set'))
    
    brightness_vals = range(init_val, end_val, step_size) + [end_val]
    if sleep_time is None:
        sleep_time = total_time / float(len(brightness_vals))
    
    for i in range(init_val, end_val, step_size):
        print i
        setBrightness(i)
        time.sleep(sleep_time)
    
        
def sendAction(action, timeout=10, num_retries=3):
    for i in range(num_retries):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        s.settimeout(timeout)
        try:
            s.connect((IPADDR, PORTNUM))
            sendActionToBridge(action, s)
            return
        except socket.timeout:
            print 'Sending action failed, retries left: {}'.format(num_retries - i - 1)
            s.close()
            
    # Did not successfully send action
#    raise(Exception('Sending message failed'))
    print 'Sending message failed'
            
def getFuncVarNames(f):
    ''' Returns the names of the parameters of f'''
    return f.__code__.co_varnames[:f.__code__.co_argcount]
    
def getFunctionSignature(action, f):
    ''' Returns instructions for how to properly call f through the command-line'''
    params = ' '.join(map(lambda x:'{}'.format(x), getFuncVarNames(f)))
    return 'python runMilight.py {} {}'.format(action, params)
    
def assertRange(val, min_val, max_val, name):
    ''' Raises Exception if val is not between min_val and max_val'''
    if not (min_val <= val <= max_val):
        raise(Exception('{} must be between {} and {}'.format(name, min_val, max_val)))
    return True
    
def sendActionToBridge(action, s):
    ''' Sends action to the wifi-bridge through s'''
    print action
    # First message    
    s.send(init_msg.decode('hex'))
    
    # Get response
    data, addr = s.recvfrom(1024) # buffer size is 1024 bytes
    print '<< response', data.encode('hex')
    
    # Last 3 bytes are an ID which must be used in the next message
    key = data.encode('hex')[-6:]
    r = resp_msg + key
    s.send(r.decode('hex'))
    
    # Send action
    r = '8000000011' + key + action
    s.send(r.decode('hex'))
    
    # Receive confirmation
    data, addr = s.recvfrom(1024) # buffer size is 1024 bytes
    response = data.encode('hex')
    print '<< response', data.encode('hex')
    
def main():
    # The valid command-line arguments and the respective functions
    function_map = {'ON' : turnOn, 
                    'OFF' : turnOff, 
                    'BRIGHTNESS' : setBrightness,
                    'HUE' : setRGB,
                    'WHITE' : setWhite,
                    'COLOR' : setColorByName,
                    'NIGHT' : setNightLight,
                    'SUNRISE' : setSunrise
                   }
    
                   
    if len(sys.argv) < 2:
        print 'Must provide at least one argument. The program can be run in the following ways:'
#        print 'python runMilight.py {} [value]'.format(function_map.keys())
        for action, f in function_map.iteritems():
            print '\t' + getFunctionSignature(action, f)
        return
    
    # First argument represents a function, 
    # if there are others then they are arguments to the function
    action = sys.argv[1].upper()
    args = sys.argv[2:]
    try:
        function_map[action](*args)
    except KeyError, e:
        # action is not in function_map
        print 'Invalid action: {}'.format(e.message)
        print 'Valid actions are: {}'.format(function_map.keys())
    except TypeError, e:
        # args are incorrect
        print 'Invalid arguments for {}'.format(action)
        print 'Action must be run as follows:'
        print getFunctionSignature(action, function_map[action])
    except Exception, e:
        # other errors
        print 'Error: {}'.format(e.message)
    
if __name__ == '__main__':
    main()
            