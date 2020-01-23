import time
from datetime import datetime
import serial
import sys
import os

#for live plotting
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
# use ggplot style for more sophisticated visuals
plt.style.use('ggplot')
line1=[]
def live_plotter(x_vec,y1_data,line1,identifier='',pause_time=0.1):
    if line1==[]:
        # this is the call to matplotlib that allows dynamic plotting
        plt.ion()
        fig = plt.figure(figsize=(13,6))
        ax = fig.add_subplot(111)
	ax.set_xticklabels([])
        # create a variable for the line so we can later update it
        line1, = ax.plot(x_vec,y1_data,'-o',alpha=0.8)        
        #update plot label/title
        plt.ylabel('Bias Current (A)')
        #plt.title('Title: {}'.format(identifier))
        #plt.show()
    
    # after the figure, axis, and line are created, we only need to update the y-data
    line1.set_ydata(y1_data)
    # adjust limits if new data goes beyond bounds
    if np.min(y1_data)<=line1.axes.get_ylim()[0] or np.max(y1_data)>=line1.axes.get_ylim()[1]:
        plt.ylim([np.min(y1_data)-np.std(y1_data),np.max(y1_data)+np.std(y1_data)])
    # this pauses the data so the figure/axis can catch up - the amount of pause can be altered above
    plt.pause(pause_time)
    
    # return line so we can update it again in the next iteration
    return line1



workingDirectory = '/home/lgad/Desktop/KeithleyCurrentMonitor'
os.chdir(workingDirectory)

def strip(myStr):
    """Gets rid of any non-alphanumeric characters that are not '-', '.', or ','
    Which is necessary because the Keithley outputs special control characters
    along with the output that we actually care about"""
    return ''.join([c for c in myStr if (c.isalnum() or c == '-' or c == '.' or c == ',' or c == ':')])

def rampVoltage(Vtarget, safeAvCurrent, deltaV):
    """Ramps voltage to a target voltage in chosen voltage increments, waiting
    for time averaged current to settle below a safe threshold before changing"""

    time.sleep(5)
    ser.flush()
    while ser.inWaiting() > 0:
        out = ser.read(1).decode("UTF-8")
    #out = ''
    #while ser.inWaiting() > 0:#flushing the buffer doesn't seem to always work?
    #    out += ser.read(1) .decode("UTF-8")
    ser.write(bytes((':SOUR:VOLT:LEV?\r').encode()))
    out = ''
    time.sleep(2)
    while ser.inWaiting() > 0:
        out += ser.read(1).decode("UTF-8")	
    print('>> ' + strip(out) + 'V')
    time.sleep(1)
    
    startVoltage = int(float(strip(out)))
    print('Ramping voltage from ' + str(int(startVoltage)) + 'V to ' + str(int(Vtarget)) + 'V')
    
    if startVoltage < Vtarget:
        deltaV = abs(deltaV)        
    elif startVoltage > Vtarget:
        deltaV = -abs(deltaV)
    elif startVoltage == Vtarget:
        return

    while 1: #loops until voltage set to Vtarget     
        currTooHigh = True
        current = []
        while currTooHigh:#waits until current settles to move on
            ser.write(bytes((':READ?\r').encode()))
            time.sleep(0.3)
            out = ''
            while ser.inWaiting() > 0:
                out += ser.read(1).decode("UTF-8")
            time.sleep(0.3)
            #this produces an output of 5 values separated by ','
            #current is the second value:
            try:
                current.append(float(strip(out).split(',')[1]))
                timeAveCurrent = sum(current[-10:])/min(len(current),10)
                if abs(timeAveCurrent) < abs(safeAvCurrent) and len(current) > 10:#less than 0.1 uA and more than 10 time averaged currents
                    currTooHigh = False
                elif(len(current)) > 1E6:
                    print('Time averaged for an extremely long time...')
                    print('Time avg current: ' +  str(timeAveCurrent))
                    current = []
            except ValueError as e:
                print('Non-critical error while ramping voltage:\n' + str(e)) #great coding style right here
                
        cmd = ':SOUR:VOLT:LEV?'
        ser.write(bytes((cmd + '\r').encode()))
        out = ''
        time.sleep(0.3)
        while ser.inWaiting() > 0:
            out += ser.read(1).decode("UTF-8")
        currVoltage = int(float(strip(out)))
        if currVoltage > 0:
            print("ERROR VOLTAGE ABOVE 0")
            ser.close()
            sys.exit()
        elif currVoltage == Vtarget:
            print('Voltage ramped to ' + str(int(currVoltage)) + 'V')
            return
        
        newVoltage = currVoltage + deltaV
        if (deltaV < 0 and newVoltage < Vtarget) or (deltaV > 0 and newVoltage > Vtarget):
            #if ramping to lower V and newVoltage is less than the target voltage
            #or if ramping to more positive V and newVoltage is above the target V
            #then I don't want to pass the desired voltage so I will set newVoltage to vTarget
            newVoltage = Vtarget
        ser.write(bytes((':SOUR:VOLT:LEV ' + str(newVoltage) + '\r').encode()))
        time.sleep(0.3)
        
        if (deltaV < 0 and newVoltage <= Vtarget) or (deltaV > 0 and newVoltage >= Vtarget):
            print('Voltage ramped to ' + str(int(newVoltage)) + 'V')
            return

def takeAndSaveData(numDP, tBtwn):
    #print('I am in takeAndSaveData')
    import time
    time.sleep(1)
    ser.flush()
    #print('Going into the while loop')
    #live plotting
    size = 1000
    x_vec = np.linspace(0,1,size+1)[0:-1]
    y_vec = np.zeros(size+1)[0:-1]
    line1=[]
    while numDP != 0: # if numDataPoints is already negative, this will indefinitely loop

        out = ''
        timeArray.append(time.time())
        ser.write(bytes((':READ?\r').encode()))
        time.sleep(0.3)#wait 0.5 sec for Keithley response
        while ser.inWaiting() > 0:
            out += ser.read(1).decode("UTF-8")
        try:
            #this produces an output of 5 values separated by ','
            #voltage is the first value
            voltageArray.append(float(strip(out).split(',')[0]))
            #current is the second value:
            currentArray.append(float(strip(out).split(',')[1]))
        except ValueError:
            time.sleep(0.5)
	    ser.flush()
	    #print('Excepted ValueError in takeAndSaveData')
            continue #try reading again if the value isn't a number
    
        time.sleep(tBtwn-0.3)#wait to take next data point, -0.5 because i already waited for 0.5s when reading data
        #save other numbers anyways, why not
        #print('About to append to timeArray')
        if voltageArray[-1] == Vtarget:
            timePlotList.append(timeArray[-1])
            currentPlotList.append(currentArray[-1])
        #print('About to append to csv file')
        with open(inpFileName, "ab") as csv_file:#append a new row to csv file
            fw = csv.writer(csv_file, delimiter=',')
            fw.writerow([voltageArray[-1], currentArray[-1], timeArray[-1], strip(out)])
            csv_file.close()
        numDP += -1

        #if numDP%2 == 0:
        y_vec[-1] = currentArray[-1]
        #line1 = live_plotter(x_vec,y_vec,line1)
        y_vec = np.append(y_vec[1:],0.0)


###--------------------------------------------------------------------------###




print('This script will tell the Keithley to slowly ramp to a chosen voltage')
print('And then monitor the current for a user-selected amount of time, in')
print('user-selected time increments')
print('If you are getting a serial open error, trying entering \'ser.close()\'\ninto the python kernel')
print('This program should ideally be run with the Keithley already set at 0V,\nwith output off')


serPort = 0 #for Scope
while 1:
    try:
        serPort = int(raw_input('What COM port (ttyS# on Linux) is the Keithley connected to?\n(You can find this by:\n\tWINDOWS: going to device hardware in the control panel\n\tLINUX: entering \'dmesg | grep -oh \"\w*tty\w*\"\' into the terminal)\n>> '))
        if serPort < 0:
            raise ValueError
        break
    except ValueError:
        print('Invalid Value, please enter a number (ex. 1 corresponds to ttyS1)')
        
# configure the serial connections (the parameters differs on the device you are connecting to
# These are the current values of the Keithley, but they can be changed
ser = serial.Serial(
	port='/dev/ttyUSB0',#S' + str(serPort),
	baudrate=9600,
	parity=serial.PARITY_NONE,
	stopbits=serial.STOPBITS_ONE,
	bytesize=serial.EIGHTBITS
)

if not ser.isOpen():
    print('Serial not opened automatically, trying again...')
    ser.open()
print('Successfully connected to Keithley')
    
ser.write(bytes('*RST\r'.encode()))
voltIncrements = 0 #for scope
while 1:
    try:
        voltIncrements = int(float(raw_input('How many volts per step up when changing voltage? (ex. 5)\n>> '))) # in Amps
        if voltIncrements > 5:
            print('You have set V/step to be ' + str(voltIncrements) + 'V')
            if str(raw_input('Are you sure that is what you meant? (Y/N)\n>> ')).lower() != 'y':
                continue
        if voltIncrements <= 0:
            raise ValueError
        break
    except ValueError:
        print('Invalid Value, please enter a positive integer')

currentCompliance = 0 #for scope
while 1:
    try:
        currentCompliance = float(raw_input('Current Compliance in amps? (ex. 1E-6, note 1nA = 1e-9A)\n>> ')) # in Amps
        if currentCompliance > 1E-6:
            print('You have set current compliance to be ' + str(currentCompliance))
            if str(raw_input('Are you sure that is what you meant? (Y/N)\n>> ')).lower() != 'y':
                continue
        break
    except ValueError:
        print('Invalid Value, please enter a number (ex. 1E-6)')
        
safeAvCurrent = 0 #for scope
while 1:
    try:
        safeAvCurrent = float(raw_input('Secondary Current Compliance in amps? (ex. 1E-6)\n>> ')) # in Amps
        if safeAvCurrent > 1E-6:
            print('You have set secondary current compliance to be ' + str(safeAvCurrent))
            if str(raw_input('Are you sure that is what you meant? (Y/N)\n>> ')).lower() != 'y':
                continue
        break
    except ValueError:
        print('Invalid Value, please enter a number (ex. 1E-6)')

#Make sure output off before calling *RST:
ser.write(bytes((':OUTP?\r').encode()))
out = ''
time.sleep(1)
while ser.inWaiting() > 0:
    a = ser.read(1)
    print a
    # if a == 0xa6:
    #     print "!!!"
    #     a = 'o'
    # print a.decode("utf-8")
    # out += ser.read(1).decode("UTF-8")
    out += a.decode("utf-8")
if strip(out) != '0':
    print('Detected output is currently on, to continue I need to reset some')
    print('Keithley settings, which will turn output off (down to 0V or 0A immediately)')
    if str(raw_input('Are you sure you want to continue? I will slowly ramp back voltage to 0 if you say yes.  (Y/N)\n>> ')).lower() != 'y':
        print('Exiting...')
        ser.close()
        sys.exit()
    else:
        rampVoltage(0, safeAvCurrent, voltIncrements)


#Set time between data collection
#Make plots looks pretty
cmdList = ['*RST',
    'SOUR:FUNC VOLT', #Set source to volt mode
    ':SOUR:VOLT:LEV 0', #Set Source to 0V
    'SENS:FUNC \"CURR\"', #Set measure to current, why you need quotes here and not on source is unknown
    ':SENS:CURR:PROT ' + str(currentCompliance)] #Set current compliance
    #':OUTPut ON', #Turn on source
    #':READ?'] #Take measurement

for cmd in cmdList:
    print("This Command: " + cmd)
    # send the command to the device
    # \r carriage return appended to the end of the command - this is requested by my device
    ser.write(bytes((cmd + '\r').encode()))
    #https://stackoverflow.com/questions/22275079/pyserial-write-wont-take-my-string
    time.sleep(0.5)
    
#Now I want to query to make sure my commands were executed successfully
cmd = 'SOUR:FUNC?'
print("Querying: " + cmd)
ser.write(bytes((cmd + '\r').encode()))
out = ''
time.sleep(1)
while ser.inWaiting() > 0:
    out += ser.read(1).decode("UTF-8")	
print(">> " + strip(out))

if strip(out) != 'VOLT':
    print("Unexpected response!! Exiting...")
    ser.close()
    sys.exit()

time.sleep(1)
cmd = ':SENS:FUNC?'
print("Querying: " + cmd)
ser.write(bytes((cmd + '\r').encode()))
out = ''
time.sleep(1)
while ser.inWaiting() > 0:
    out += ser.read(1).decode("UTF-8")	
print(">> " + strip(out))
if strip(out) != 'CURR:DC':
    print("Unexpected response!! Exiting...")
    ser.close()
    sys.exit()

time.sleep(1)
cmd = ':SOUR:VOLT:LEV?'
print("Querying: " + cmd)
ser.write(bytes((cmd + '\r').encode()))
out = ''
time.sleep(1)
while ser.inWaiting() > 0:
    out += ser.read(1).decode("UTF-8")	
print(">> " + strip(out))
if float(strip(out)) != 0:
    print("Unexpected response!! Exiting...")
    ser.close()
    sys.exit()

time.sleep(1)
cmd = ':SENS:CURR:PROT?'
print("Querying: " + cmd)
ser.write(bytes((cmd + '\r').encode()))
out = ''
time.sleep(1)
while ser.inWaiting() > 0:
    out += ser.read(1).decode("UTF-8")	
print(">> " + strip(out))
if float(strip(out)) != currentCompliance:
    print("Unexpected response!! Exiting...")
    ser.close()
    sys.exit()

print("Initial commands verified executed...")
inp = raw_input("OK To turn on output? (Y/N)\n>> ")
if str(inp).lower() == 'y':
    print("Turning on output")
else:
    print("No output. Exiting")
    ser.close()
    sys.exit()

cmd = ':OUTPut ON'
print("This Command: " + cmd)
ser.write(bytes((cmd + '\r').encode()))
time.sleep(1)

inpFileName = ''
timeStamp = datetime.utcnow().strftime('UTC%b%d%Y+%H.%M.%S').upper()
#defaultFileName = 'V(' + str(int(Vtarget)) + ')_numDP(' + str(numDataPoints) + ')_' + timeStamp + '_CurrMonit'
defaultFileName = 'CurrMonit_' + timeStamp
inpFileName = str(raw_input('Please enter a filename to write to (no extension needed)\nOr just press enter and the default name will be \n\'' + defaultFileName + '.csv\'\n>> '))
if inpFileName == '':
    inpFileName = defaultFileName
    
if not inp.lower().endswith('.csv'):
    inpFileName += '.csv'
    
#create csv file to write to:
import csv
with open(inpFileName, "wb") as csv_file:
    fw = csv.writer(csv_file, delimiter=',')
    fw.writerow(['Voltage (V)','Current (A)', 'Time (s)','Raw Keithley Ouput from :READ? command'])
    csv_file.close()
    
print('CSV Successfully created')
## --------------------- End Setup Process ----------------------- ##

try:
    while 1:
        #Set max voltage, in Volts, this value must be negative
        VList = [] #for scope
        while 1:
            try:
		dV = 20
                tempV = strip(str(raw_input('Target voltages, in volts? (ex. -100,-100:-120,-110)\n(Entering a range (-a:-b) will go in {}V steps)\n>> '.format(dV)))).split(',')
                for istr in tempV:
		    if ':' in istr:
			tempstr = istr.split(':')
			if len(tempstr) == 3:
			     dV = abs(int(tempstr[2]))
			     print 'Entered a custom value for range: {}V'.format(dV)
			if int(tempstr[0]) > 0 or int(tempstr[1]) > 0:
			     raise ValueError
			elif int(tempstr[0])<int(tempstr[1]):
			     for voltageRangeVal in range(int(tempstr[0]), int(tempstr[1])+dV,+dV):#Create range of voltages in -10V increments
			          VList.append(voltageRangeVal)
			elif int(tempstr[0])>int(tempstr[1]):
			     for voltageRangeVal in range(int(tempstr[0]), int(tempstr[1])-dV,-dV):#Create range of voltages in +10V increments
			          VList.append(voltageRangeVal)
			continue

                    VList.append(int(istr))
                    if int(istr) > 0:
                        raise ValueError
		print('You entered:\n' + str(VList))
                break
            except ValueError:
                VList = []
                print('Invalid Value, please enter a list of negative integers')
            
        numDataPoints = 0 #for scope
        while 1:
            try:
                numDataPoints = int(raw_input('How many data points would you like to collect? (ex. 100)\nYou may enter -1 for indefinite data-taking\n>> ')) # in Amps
                if numDataPoints == -1:
                    pass
                elif numDataPoints < 1:
                    raise ValueError
                break
            except ValueError:
                print('Invalid Value, please enter a positive integer')
            
        timeBtwnData = 0 #for Scope   
        while 1:
            try:
                timeBtwnData = float(raw_input('How often should data be taken, in seconds?\n>> '))
                if timeBtwnData <= 0.3:
                    raise ValueError
                break
            except ValueError:
                print('Invalid Value, please enter a number greater than 0.3 (ex. 10.2)')

	timeToWait = 0 #for Scope   
        while 1:
            try:
                timeToWait = float(raw_input('How long do you want to wait before taking data, in seconds?\n>> '))
                if timeToWait < 0:
                    raise ValueError
                break
            except ValueError:
                print('Invalid Value, please enter a positive number (ex. 10.2)')
        
        #Estimated time to completion
        if numDataPoints != -1:
            estTime = numDataPoints*timeBtwnData/3600#in hours
            print('It is currently ' + datetime.utcnow().strftime('UTC%Y-%m-%d%H:%M:%S.%f')[:-3])
            print('This will take approximately ' + str(estTime) + 'hrs')
        
        print('Will now begin gathering data at')
        print('The procedure is as follows:')
        print('\t1. Ramp voltage')
        print('\t2. Take ' + str(numDataPoints) + ' data points at each voltage, waiting ' + str(timeBtwnData) + 's between')
        print('\t3. Populate a CSV file with that data')
        
        ser.flush() #just in case
        #begin collecting data:
        voltageArray = []
        currentArray = []
        timeArray = []
        currentPlotList = []#only currents at the voltage Vtarget are plotted
        timePlotList = []   #and their corresponding times
        try:
            for Vtarget in VList:
                rampVoltage(Vtarget, safeAvCurrent, voltIncrements)
        	time.sleep(timeToWait)
                if numDataPoints == -1:
                    print('To end data taking at this voltage, interrupt with \'ctrl+c\'')
                try:
                    takeAndSaveData(numDataPoints, timeBtwnData)
                    plt.close()
                except Exception as e:
                    print('\nUser Interrupt, going to next voltage')
                    ser.flush()
                    csv_file.close()
                    plt.close()
        except KeyboardInterrupt:
            print('\nUser Interrupt, going back to input settings')
            ser.flush() #clear anything in buffer
            csv_file.close()
except KeyboardInterrupt:
    print('\nUser Interrupt, all done')
    ser.flush()
    csv_file.close()
    
#from matplotlib import pyplot as plt
#plt.figure()
#plt.plot(timePlotList, currentPlotList)
#plt.title('Current vs. Time at ' + str(Vtarget) + 'V')
#plt.xlabel('Time (s)')
#plt.ylabel('Current (uA)')
#plt.show()

print('Ramping Down')
rampVoltage(0, safeAvCurrent, voltIncrements)

print('Goodbye')
ser.close()
