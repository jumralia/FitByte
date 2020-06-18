import serial
import pyrebase
import firebase_admin
from google.cloud import firestore
from firebase_admin import credentials, firestore
from time import sleep
############################ ADDED ############################################
import math as m
import time
from pusher_push_notifications import PushNotifications
############################# ADDED ENDED ##################################################
# import bluetooth

# TODO /dev/ttyXXX is connection specific
port = serial.Serial('/dev/rfcomm0', baudrate=115200, timeout=1.0)
# hostMAC = '20:19:03:27:34:06'
# portNum = 3
# backlog = 1
# size = 1024
# port = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
# port.bind(hostMAC, portNum)
# port.listen(backlog)

# TODO byteorder (big or little) need to be corrected
portwrite = "/dev/ttyUSB2"
portExtra = "/dev/ttyUSB1"
endian = 'little'

config = {
        "apiKey": "AIzaSyDXqpsFQ8vHNvmxOMEON3L_zPmPWUZOzlo",
        "authDomain": "fitbyte-fitbyte.firebaseapp.com",
        "databaseURL": "https://fitbyte-fitbyte.firebaseio.com",
        "storageBucket": "fitbyte-fitbyte.appspot.com"

}

firebase = pyrebase.initialize_app(config)
cred = credentials.Certificate('./fitbyte-fitbyte-firebase-adminsdk-s6905-6104a6607a.json')
fs = firebase_admin.initialize_app(cred)
db = firebase.database()
db_FireStore = firestore.client()

beams_client = PushNotifications(
    instance_id='a194b3e8-beab-4ceb-a831-4f3b45eddc96',
    secret_key='209B915E1261D6CDC828F9296D35F5A413D738E08D0D514A3E4B83E5E60668BC',
)

total_accl=[]                   # List of two acceleration values.
alert_state=0                   # state (0/1) says whether to be alert and start counting the switches or be relaxed.
change=0                        # Single value representing switch nature.
switches=0                      # Measure of number of tremors.
cautious_state=0                # State 1 or 0 indicating whether the system needs to enter cautious state or not.
switch_nature=[]
switch_sample=[]




def parseGPS(data):
    print ("raw:"), data #prints raw data
    if data[0:6] == "$GPRMC".encode():
        sdata = data.split(",".encode())
        if sdata[2] == 'V'.encode():
            print ("no satellite data available")
            return
        print ("-----Parsing GPRMC-----")
        time = sdata[1][0:2] + ":".encode() + sdata[1][2:4] + ":".encode() + sdata[1][4:6]
        lat = sdata[3] #latitude
        dirLat = sdata[4]      #latitude direction N/S
        lon = sdata[5] #longitute
        dirLon = sdata[6]      #longitude direction E/W
        speed = sdata[7]       #Speed in knots
        trCourse = sdata[8]    #True course
        date = sdata[9][0:2] + "/".encode() + sdata[9][2:4] + "/".encode() + sdata[9][4:6]
                           #date
        variation = sdata[10]  #variation
        degreeChecksum = sdata[12]
        dc = degreeChecksum.split("*".encode())
        degree = dc[0]        #degree
        checksum = dc[1]      #checksum
        #l1 = str(sdata[3],'utf-8')
        #print(str(lat,'utf-8'))
        #l2 = sdata[5]
        if str(dirLat,'utf-8') == 'N':
            cv = str(lat,'utf-8')
            aLat1 = str(int(float(cv)/100))
            aLat2 = str((float(cv)/100 - int(float(cv)/100)))
            aLat3 = aLat2.translate({ord('0'):None})
            aLat4 = aLat3.translate({ord('.'):None})
            aLat5 = int(float(aLat4)/60)
            bLat = aLat1 + "." + str(aLat5)
        else:
            cv = str(lat,'utf-8')
            aLat1 = str(int(float(cv)/-100))
            aLat2 = str((float(cv)/100 - int(float(cv)/100)))
            aLat3 = aLat2.translate({ord('0'):None})
            aLat4 = aLat3.translate({ord('.'):None})
            aLat5 = int(float(aLat4)/60)
            bLat = aLat1 + "." + str(aLat5)
        if str(dirLon,'utf-8') == 'W':
            cv = str(lon,'utf-8')
            aLon1 = str(int(float(cv)/-100))
            aLon2 = str((float(cv)/100 - int(float(cv)/100)))
            aLon3 = aLon2.translate({ord('0'):None})
            aLon4 = aLon3.translate({ord('.'):None})
            aLon5 = int(float(aLon4)/60)
            bLon = aLon1 + "." + str(aLon5)
        else:
            cv = str(lon,'utf-8')
            aLon1 = str(int(float(cv)/100))
            aLon2 = str((float(cv)/100 - int(float(cv)/100)))
            aLon3 = aLon2.translate({ord('0'):None})
            aLon4 = aLon3.translate({ord('.'):None})
            aLon5 = int(float(aLon4)/60)
            bLon = aLon1 + "." + str(aLon5)
        db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"familyMemberLatitude":bLat})
        db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"familyMemberLongitude":bLon})
        print ("time : %s, latitude : %s(%s), longitude : %s(%s), speed : %s, True Course : %s, Date : %s, Magnetic Variation : %s(%s),Checksum : %s "%    (time,lat,dirLat,lon,dirLon,speed,trCourse,date,variation,degree,checksum))
        #print ("Latitude is %s(%s)", l1)
    else:
        print ("Printed data is ",data[0:6])
def decode(coord):
    #Converts DDDMM.MMMMM -> DD deg MM.MMMMM min
    x = coord.split(".")
    head = x[0]
    tail = x[1]
    deg = head[0:-2]
    min = head[-2:]
    return (deg + " deg " + min + "." + tail + " min")

print ("Connecting port")
serw = serial.Serial(portwrite, baudrate = 115200, timeout = 1,rtscts=True, dsrdtr=True)
serw.write(('AT+QGPS=1\r').encode())
serw.close()
sleep(0.5)

print ("Receiving GPS data")
ser = serial.Serial(portExtra, baudrate = 115200, timeout = 0.5,rtscts=True, dsrdtr=True)

start_time=time.time()
print(start_time)





while True:
    #data = ser.readline()                          # This line is used to read the GPS ports
    #parseGPS(data)
   
    if (len(total_accl)<120):                                    # Collecting all 1 second samples
        
            ##### Collect accelerometer data ##################################
        firstbyte = port.read()                     #read 1 byte of the sensor
        if firstbyte == bytes.fromhex('55'):           # start of data package
            
            secondbyte = port.read()                     #read next byte
            if secondbyte == bytes.fromhex('51'):      # start of acceleration data
                
                accel = []
                for i in range(3):      #read next 3x2bytes and convert to interger
                    accel.append(int.from_bytes(port.read(2), byteorder=endian, signed=True)/32768.0*16)
                # temp = int.from_bytes(port.read(2), byteorder=endian, signed=True)/340.0+36.25
                   
                
                
                x = accel[0]                                  
                y = accel[1]
                z = accel[2]

                
                a=m.sqrt(x*x+y*y+z*z)
                print(a)
                #print("Got acceleration value of " + str(a)+ " at time: "  + str(time.time()))
                total_accl.append(a)        
                
    
    else:
        
        print("In process")
        
        ############# Do processing ####################################
        if (alert_state==0 and cautious_state==0):

            for sample_number in range(1,len(total_accl)):
                if (total_accl[sample_number]>total_accl[sample_number-1]):
                    switch_nature.append(1)
                    switch_sample.append(sample_number)
                elif (total_accl[sample_number]<total_accl[sample_number-1]):
                    switch_nature.append(-1)
                    switch_sample.append(sample_number)
                if (len(switch_nature)>1 and switch_nature[-1]!=switch_nature[-2] and (switch_sample[-1]-switch_sample[-2])<=8):                   # TODO: How many ever samples 0.2 sec is.... Do the calculation first!!!
                    
                    print("ENTERING ALERT STATE (LESS THAN 8 SAMPLE DIFFERENCE)")
                    alert_state=1
                    switches=0                                                                                                                  # TODO: Brainstorm to check if this needs to be made 1.                                                                                                                 
                    
                    break
            print("Switch Nature " + str(switch_nature))
            print("total_ acc -1 "+ str(len(total_accl)-1))
            print("Sample number "+ str(sample_number))
            if (sample_number==(len(total_accl)-1)):
                print("Full loop done")
            total_accl=[]
            switch_nature=[]
            switch_sample=[]
            
            continue
            
                
                
                                                                                                                       
    
        
        if ((alert_state==1) and (cautious_state==0)):
            print("Inside alert state")
            for sample in range(1,len(total_accl)):                                                                          # TODO: Check if the number of samples in a second is indeed 120. Hard code that number here.
                if (total_accl[sample]>total_accl[sample-1]):
                    switch_nature.append(1)
                    if (len(switch_nature)>1  and switch_nature[-1]!=switch_nature[-2]):
                        switches+=1
                elif (total_accl[sample]<total_accl[sample-1]):
                    switch_nature.append(-1)
                    if (len(switch_nature)>1  and switch_nature[-1]!=switch_nature[-2]):
                        switches+=1
                
                
            print("Switches " +str(switches))    
            if switches>=8:
                print("SEIZURE DETECTED!!!")
                alert_state=0
                switches=0
                total_accl=[]
                switch_nature=[]
                switch_sample=[]

                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(1)
                db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":1})  # add this line when seizure happened


                def stream_handler(message):
                    #print(message)
                    if(message['data'] is 1):
                        response = beams_client.publish_to_interests(
                        interests=['hello'],
                        publish_body={
                            'apns': {
                                'aps': {
                                    'alert': 'Hello!',
                                },
                            },
                            'fcm': {
                                'notification': {
                                    'title': 'Pay Attention: ',
                                    'body': 'The seizure is happened',
                                },
                            },
                        },
                    )

                        print(response['publishId'])
                # db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(1)
                #db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":1})  # add this line when seizure happened
               

                
                    
                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").stream(stream_handler,None)
                
                
                 ### Send the GPS data ###
                data = ser.readline()
                parseGPS(data)
                ##### Finished GPS #####
                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(0)
                db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":0})  # add this line when seizure happened
                
                continue
                
            elif(switches>=5 and switches<8):
                print(" Hold On -- Entering Cautious state")
                cautious_state=1
                alert_state=0
                switches=0
                total_accl=[]
                switch_nature=[]
                switch_sample=[]
                continue                                                                                                        # TODO: Check if it means continue with the while loop.
                
                # Go ahead and colllect 120 more samples and repeat the above procedure for alert state seizure detection.
            else:
                alert_state=0
                cautious_state=0
                switches=0
                total_accl=[]
                switch_nature=[]
                switch_sample=[]
                continue
            
    
        if ((alert_state==0) and (cautious_state==1)):
            
            for s in range(1,len(total_accl)):                              # Will throw error if number of samples in 1 sec not 121.                                 # TODO: Check if the number of samples in a second is indeed 120. Hard code that number here.
                if (total_accl[s]>total_accl[s-1]):
                    switch_nature.append(1)
                    if (len(switch_nature)>1 and switch_nature[-1]!=switch_nature[-2]):
                        switches+=1
                elif (total_accl[s]<total_accl[s-1]):
                    switch_nature.append(-1)
                    if (len(switch_nature)>1 and switch_nature[-1]!=switch_nature[-2]):
                        switches+=1
                
                
                
            if switches>=8:
                print(" SEIZURE DETECTED!!!")
                cautious_state=0
                switches=0
                total_accl=[]
                switch_nature=[]
                switch_sample=[]

                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(1)
                db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":1})  # add this line when seizure happened


                def stream_handler(message):
                    #print(message)
                    if(message['data'] is 1):
                        response = beams_client.publish_to_interests(
                        interests=['hello'],
                        publish_body={
                            'apns': {
                                'aps': {
                                    'alert': 'Hello!',
                                },
                            },
                            'fcm': {
                                'notification': {
                                    'title': 'Pay Attention: ',
                                    'body': 'The seizure is happened',
                                },
                            },
                        },
                    )

                        print(response['publishId'])
                # db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(1)
                #db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":1})  # add this line when seizure happened
               

                
                    
                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").stream(stream_handler,None)
                
                ### Send the GPS data ###
                data = ser.readline()
                parseGPS(data)
                ##### Finished GPS #####

                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(0)
                db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":0})  # add this line when seizure happened
                
                continue                                                                            # TODO: Check where it continues. Need to continue the while loop

            
            
            elif (switches>=5 and switches<8):
                print("MILD INTENSITY SEIZURE DETECTED (With 8 tremors in a second)")
                cautious_state=0
                switches=0
                total_accl=[]
                switch_nature=[]
                switch_sample=[]

                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(1)
                db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":1})  # add this line when seizure happened

                def stream_handler(message):
                    #print(message)
                    if(message['data'] is 1):
                        response = beams_client.publish_to_interests(
                        interests=['hello'],
                        publish_body={
                            'apns': {
                                'aps': {
                                    'alert': 'Hello!',
                                },
                            },
                            'fcm': {
                                'notification': {
                                    'title': 'Pay Attention: ',
                                    'body': 'The seizure is happened',
                                },
                            },
                        },
                    )

                        print(response['publishId'])
                # db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(1)
                #db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":1})  # add this line when seizure happened
               

                
                    
                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").stream(stream_handler,None)


                
                ### Send the GPS data ###
                data = ser.readline()
                parseGPS(data)
                ##### Finished GPS #####
                db.child("Fitbyters' Database").child("npUD9N1UX0MVlixYa9gQSw0fDtd2").child("alertMessage").set(0)
                db_FireStore.collection("Fitbyters' Database").document("npUD9N1UX0MVlixYa9gQSw0fDtd2").update({"alertMessage":0})  # add this line when seizure happened
                
                continue
            
            else:
                cautious_state=0
                switches=0
                total_accl=[]
                switch_nature=[]
                switch_sample=[]
                continue
                
                


################################################ ADDED ENDED##########################################################################            
            print("Finished processing at time: "+str(time.time()))


#        elif secondbyte == bytes.fromhex('52'):    # start of angle velocity data
#            angVel = []
#            for i in range(3):
#                angVel.append(int.from_bytes(port.read(2), byteorder=endian, signed=True)/32768.0*2000)
#            # temp = int.from_bytes(port.read(2), byteorder=endian, signed=True)/340.0+36.25
#           # print("Angular Velocity:")
#           # print(angVel)
#        elif secondbyte == bytes.fromhex('53'):    # start of angle data
#            angle = []
#            for i in range(3):
#                angle.append(int.from_bytes(port.read(2), byteorder=endian, signed=True)/32768.0*180)
            # temp = int.from_bytes(port.read(2), byteorder=endian, signed=True)/340.0+36.25
           # print("Angle:")
           # print(angle)
