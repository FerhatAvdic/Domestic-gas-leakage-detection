import sys, time
import RPi.GPIO as GPIO
import Adafruit_ADS1x15
import smtplib
import math
from urllib2 import urlopen

# Define smtp and send email
def sendEmail():
	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login("ferhat.avdic@gmail.com", "135_buhnij_680")

	msg = "GAS SENSOR WARNING!"
	server.sendmail("ferhat.avdic@gmail.com", "ferhat.avdic@gmail.com", msg)
	server.quit()
 
def MQGetPercentage(rs_ro_ratio, pcurve):
	 return (math.pow(10,( ((math.log(rs_ro_ratio)-pcurve[1])/ pcurve[2]) + pcurve[0])))

######## SETUP VARS #########

writeAPI = "3454BQPZ0MGOGJPW"
baseURL = 'https://api.thingspeak.com/update?api_key=%s' % writeAPI
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.IN)
adc = Adafruit_ADS1x15.ADS1115()
R0 = 9.83
sensorValue = 0.0

LPGCurve = [2.3,0.21,-0.47]    # two points are taken from the curve. 
									# with these two points, a line is formed which is "approximately equivalent"
									# to the original curve. 
									# data format:{ x, y, slope}; point1: (lg200, 0.21), point2: (lg10000, -0.59) 
COCurve = [2.3,0.72,-0.34]     # two points are taken from the curve. 
									# with these two points, a line is formed which is "approximately equivalent" 
									# to the original curve.
									# data format:[ x, y, slope]; point1: (lg200, 0.72), point2: (lg10000,  0.15)
SmokeCurve =[2.3,0.53,-0.44]   # two points are taken from the curve. 
									# with these two points, a line is formed which is "approximately equivalent" 
									# to the original curve.
									# data format:[ x, y, slope]; point1: (lg200, 0.53), point2: (lg10000,  -0.22) 

######## INITIAL CALIBRATION ########

try:
	print("Press CTRL+C to abort.")
	
	# Read 100 times to get average
	for x in range(100):
		sensorValue = sensorValue + adc.read_adc(0, gain=1)
	
	# Get average sensor value
	sensorValue = sensorValue/100.0
	
	# Calc sensor voltage
	sensor_volt = sensorValue/1024*5.0
	
	# Clean air sensor resistance
	RS_air = (5.0-sensor_volt)/sensor_volt
	
	# The ratio of RS/R0 is 9.8 in a clear air from Graph (Found using WebPlotDigitizer)
	R0 = RS_air/9.8
	
	print("\nCalibrated values\n")
	print("sensor_volt =  %g V" % sensor_volt)
	print("R0 = %g\n" % R0)
	
	
	# MAIN LOOP
	while True:
		# Get sensor digital value
		adc_d0 = GPIO.input(11)
		# Get sensor analog value
		sensorValue = adc.read_adc(0, gain=1)
		# Calc voltage
		sensor_volt=float(sensorValue)/1024*5.0
		if (sensor_volt > 4):
			sensor_volt = 4
		# Calc resistance
		RS_gas = (5.0-sensor_volt)/sensor_volt
		# Calc ratio
		ratio = RS_gas/R0
		lpg = MQGetPercentage(ratio, LPGCurve)
		co = MQGetPercentage(ratio, COCurve)
		smoke = MQGetPercentage(ratio, SmokeCurve)

    updateGraphsURL = baseURL + "&field1=%s&field2=%s&field3=%s" % (sensor_volt, RS_gas, ratio)
		f = urllib.request.urlopen(updateGraphsURL)
		f.close()
		
		# Value output
		sys.stdout.write("\r")
		sys.stdout.write("\033[K")
		sys.stdout.write("sensor_volt =  %g V\tRS_ratio = %g\tRs/R0 =  = %g" % (sensor_volt, RS_gas, ratio))
		sys.stdout.write("\r")
		sys.stdout.write("\033[K")
		sys.stdout.write("LPG = %g ppm\tCO = %g ppm\tSMOKE = %g ppm" % (lpg,co,smoke))
		
		# If gas concentration is critical send warning email
		if (adc_d0 == 0):
			sendEmail()
			print("\nWarning Sent")
			break
			
		sys.stdout.flush()
		time.sleep(0.3)
		
except ValueError:
	sendEmail()
	print("\nSensor overload, warning Sent")

except:
	print("\nAbort by user")
	print("Unexpected error:", sys.exc_info()[0])
	raise
	