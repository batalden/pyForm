import serial #Serial module, opens and sends to serial ports
import random #Currently unused
import math
import time

'''
6/21/2024
inForm testing code
Written by Amos Batalden
Python script written for testing and running the inForm Shape Display
in preparation for its two-year stay at the MIT Museum.
Adapted from the older C++ OpenFrameworks code base

This code communicates with the inForm Shape Display in the simplest way I could.
Below is a breakdown of how the display is set up and a brief explanation of the
code that runs on the boards that control the motors.

The inForm runs on 96 chips running Arduino code. Each arduino code controls 6 pins.
The chips are sent information through 3 serial connections. Signals sent this way
go to every board on a given serial connection, and the arduino code discards the
information if it's not meant for that board.

Throughout the code, there are lines like this:

sendToBoard(port1, i, pins, True)
sendToBoard(port2, i, pins, True)
sendToBoard(port3, i, pins, True)

This is a somewhat lazy solution that takes advantage of the fact that the boards
discard irrelevant messages. By sending the same message to all the boards, we
don't have to worry about which board is on which serial connection.

Messages sent to the boards are "bytearray"s. They take this format:
[termID, boardID, int, int, int, int, int, int]

Each "int" is sent to one of the 6 pins controlled by that chip.

boardID is an integer that identifies the board that the message is meant for.
There are 96 boards on the inForm, and they are 1-indexed, so the lowest ID is 1
and the highest ID is 96.

termID is a number higher than 246 that tells the board what kind of message is being sent.
No other byte sent to the arduino is higher than 246. This is used to identify the start of
a new message, since multiple bytearray messages are receieved by the boards as a single
stream of bytes.

Below is a key for what each number means.
246: Send heights, signals the board to not reply back with its own detected pin heights.
247: Set the proportional gain
248: Set the integral gain
249: Set the max integral
250: Set the dead zone
251: Set the gravity compensation (unused in both the C++ code and here as of 6/21/24, probably should be set)
252: Sets the max speed
253: Request a reply with the board's deteced pin heights
254: Send heights and request a reply with the boards detected pin heights.

Replies from the board have the same format, except where the "termID" would be is always the number 253.
This concludes the message format. Below is an ASCII representation of a top view of the inForm.
  _____________
 |             |
 |             |
 |             |
 |             |
 |             |
 |             |
 |____XXXXX____|

 The Xs represent the power supply.
 This code implements a coordinate system to better describe the patterns we send to the shape display.
 The coordinate system starts at (0,0) in the top left corner of the ASCII drawing and goes to (23,23)
 at the bottom right. The top right corner is (23,0) and the bottom left is (0,23).

 The board layout is as follows:
 There are four boards controlling a section of 6 adjacent pins on each row where y is constant.
 The board ids for the first row (from left to right) are 1,2,3,4. The boardIDs for
 the second row (again from left to right) are 9,10,11,12. The third row has
 5,6,7,8. I don't know why it's like this. It's not a typo. The 6 "message content"
 bytes correspond to the pins in the opposite direction of the board arrangement.
 Curiously, this is also the case for the upside-down boards.

 So a message sent to board id 1 with content [200, 50, 50, 50, 50, 50] would raise the pin with
 coordinates (5,0). The function coordToPin does this for you. We could find the board ID and
 pin index above with

 >>>coordToPin(5,0)

 which would return:

 [1,0]
 
 The pin index (the second element of this output list) is 0-indexed.
 You can read the coordToPin function for further details.

'''



def list_ports(): #Stupid function which guesses ports 
    ports = []    #as a way of listing them.
    print('finding ports')
    for i in range(0,15): #This can't be the right way to do this.
        try:
            port = serial.Serial('COM' + str(i))  #Currently unused but useful to call after halting excecution 
            ports.append('COM' + str(i))          #if you don't know what the port names are.
            port.close()
            print('found port ' + 'COM' + str(i))
        except:
            print('tried to open non-existant port ' + 'COM' + str(i))
            continue
    print('done')
    return ports

def sendToBoard(boardID, values, reply, config = False, inTermID = None): #The only function that actually writes to the serial ports.
    
    if not config: #config is a boolean which is true when sendToBoard is being used to update the control parameters of the motor.
        flipped = ((boardID-5)%12) < 4  #Some of the boards are installed "upside down". Because of this, when pin heights are sent to the board,
        if reply:                       #the value needs to have its sign flipped and added with 255.
            termID = 254  #See note at the top about the arduino code for an explanation of termID
        else:
            termID = 246
        message = [termID,boardID] + values #The message is ultimately an array of bytes, but we assemble it as a list of integers.
        if flipped:                             #Convention for message format is explained at the top of the file, but it starts with a number (the termID) higher than 245
            message[2:] = [260-i for i in message[2:]]  #then has its content. This is read until the next number greater than 245 (the start of the next message)       
    else:                                   
        message = [inTermID,boardID] + values #When sending config, the termID is included in the inputs, and flipped boards are no longer a concern.
    byteMessage = bytearray(message)
    if boardID < 37:
        port = port3
    elif boardID < 61:
        port = port2
    else:
        port = port1
    port.write(byteMessage)

def read(port, wait = True):                 #Unused as of 6/21/24. Reads a message from a board and returns it as a dict.
    result = {}                              #The dicts look like this: {'boardID':43,'faderPositions':[55,55,200,55,55,55]}
    if wait:                                 #Reads one entire message.
        currentByte = port.read(1)
    else:
        currentByte = port.read(1)
    while currentByte != 253:   #253 is what the board sends as its "termID" -- an identifier of the message's type that doubles as an indicator that a message is starting.
        currentByte = port.read(1)
    result['boardID'] = port.read(1)
    result['faderPositions'] = []
    for i in range(6):
        result['faderPositions'].append(port.read(1))
    return result

def coordToPin(x,y):                              #Converts an x and y coordinate to the board ID and pin number. 
    boardNumX = math.ceil((x+1)/6)                #Coordinate system is explained at the top of the file.
    boardNumsY = []
    for i in range(8):
        boardNumsY += [1+12*i,9+12*i,5+12*i]
    boardNumY = boardNumsY[y]
    boardNum = boardNumY + boardNumX-1
    pinNum = (-(x+1)%6)
    return [boardNum,pinNum]


def sendFullResetTo55(): #Pin control function. Resets the whole board to 55, slightly above the absolute minimum value 50.
    pins = [55,55,55,55,55,55]
    for i in range(96):
        sendToBoard(i, pins, True)


def sendFullResetToValue(port1,port2,port3,value): #Pin control function. Resets the whole board to 55, slightly above the absolute minimum value 50.
    pins = [value]*6
    for i in range(96):
        sendToBoard(i, pins, True)


def sendIndividualPinValue(x,y,value): #Pin control function. Sets one pin on the board to a specified value,
    location = coordToPin(x,y)                           #resets the other pins on that board to 55.
    boardID = location[0]
    pinNumber = location[1]
    pins = [55]*6
    pins[pinNumber] = value
    #sendToBoard(port1, boardID, pins, True)
    sendToBoard(boardID, pins, True)
    #sendToBoard(port3, boardID, pins, True)



def sendSinFunction(inT=0):  #Sends a 3d function to the pins with an optional time argument to simulate motion. 
    t = inT                                  #The function is a transformation of sin(x)sin(y).
    bunches = []
    pinList = []
    for x in range(24):
        for y in range(24):
            pinList.append([int(100*((math.sin((x-t)/10)*math.sin((y-t)/10))**2)+60)] + coordToPin(x,y))
    sendValXYsToBoard(pinList)


def sendValXYsToBoard(valXYs):
    for i in range(96):
        pins = [50,50,50,50,50,50]
        for pinIndex in range(len(valXYs)):
            if valXYs[pinIndex][1] == i:
                pins[valXYs[pinIndex][2]] = int(valXYs[pinIndex][0])

        if i == 67:
            pins[2] = 55
        sendToBoard(i, pins, True)

    
        

def sendDefaultConfigs(boardNum = None): #Sends the default configuration to the boards, as recorded in the C++ OpenFrameworks code base
    gainP = 1.5
    gainI = 0#0.045
    maxI = 25
    deadZone = 2
    maxSpeed = 200
    
    configs = [gainP, gainI, maxI, deadZone, maxSpeed]
    termIDs = [247, 248, 249, 250, 252]
    multipliers = [25, 100, 1, 1, 1/2] #This is an odd protocol that we have to follow because the arduinos are expecting these numbers to be multiplied by these values.
                                       #Since some of these numbers are not integers, they were multiplied to be larger so that they would fit in a byte.
                                       #Not sure why maxSpeed is halved. Maybe they were worried that it would be read as a signed int "-72" since it has a leading 1.
    configs = [configs[i]*multipliers[i] for i in range(len(configs))]
    if not boardNum:
        for i in range(len(configs)):
            for n in range(1,97):
                sendToBoard(n, [int(configs[i])]*6, False, config = True, inTermID = termIDs[i])

    else:
        sendToBoard(boardNum, [int(configs[i])] * 6, False, config = True, inTermID = termIDs[i])
        
                

print('connecting')

port1 = serial.Serial('COM7',  115200, timeout=1)  #Opens the ports. On my (Amos Batalden) computer, the ports get these names when I connect to the inForm.
port2 = serial.Serial('COM8',  115200, timeout=1)  #On your machine you'll have to interrupt excecution and run the list_ports() function with and without the inForm
port3 = serial.Serial('COM10',  115200, timeout=1) #connected to deduce which ports connect to the machine. Alternatively, you could write a function that sends 
sendDefaultConfigs()                  #messages to each port with term ID 253 (request heights), then identify the ports that way.


#  -------------------------------------------------------
#  Code below here determines what the shape display plays.
#  -------------------------------------------------------



#sendFullResetTo55(port1,port2,port3)
#sendIndividualPinValue(port1,port2,port3,0,0,140)



#sendFullResetToValue(port1,port2,port3,55)

#for i in range(60,200):
#    pinList = []
#    for x in range(24):
#        pinList.append([i,x,0])
#    sendValXYsToBoard(pinList,port1,port2,port3)







sendFullResetTo55()  #simple diagnostic that fires each pin one at a time
'''
for i in range(5):
    for x in range(24):
        for y in range(24):
            if not (x == 0 and y == 0):
                sendIndividualPinValue(lastPin[0],lastPin[1],55)
            sendIndividualPinValue(x,y,200)
            lastPin = [x,y]
            time.sleep(0.1)
'''
for i in range(1000):
    sendSinFunction(i)
    time.sleep(0.05)



