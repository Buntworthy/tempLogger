#!/usr/bin/python

################## TEMP LOGGING ##################
#
# Temperature logging to csv file on RPi
#
# Currently just log the previous 7 days of
# measurements to a csv file, any older
# measurements are just discareded.
#
##################################################

import sys
import time
import datetime
import csv
from ftplib import FTP

# import Adafruit_DHT

################ Program constants ################

# Sensor details
# DHT_TYPE = Adafruit_DHT.DHT22
DHT_PIN  = 4

# How long to wait (in seconds) between measurements.
FREQUENCY_SECONDS      = 3

# How many times to retry any reading
READING_RETRIES = 5

# Filenames
SETTINGS_FILENAME = 'config.csv'
DATA_FILENAME = 'data.csv'

# How much data to store (hours)
HISTORY_LENGTH = 0.02

###################################################

# Create measurement variables
timeData = []
tempData = []
humiData = []

# Read in the existing data if it is there
dataFile = open(DATA_FILENAME,'rb')
dataReader = csv.reader(dataFile)
for row in dataReader:
	# load time
	loadTime = datetime.datetime.strptime(
		row[0],
		'%Y-%m-%d %H:%M:%S.%f')

	timeData.append(loadTime)
	tempData.append(row[1])
	humiData.append(row[2])

dataFile.close()

# Load the FTP access details
configFile = open(SETTINGS_FILENAME,'rb')
configReader = csv.reader(configFile)
config = {rows[0]:rows[1] for rows in configReader}
host = config['host']
user = config['user']
pword = config['pword']

# Set up FTP access object
ftp = FTP(host)
try:
	print('Logging into ftp server ' + host)
	ftp.login(user, pword)

except Exception, e:
	print('Failed to log into FTP server')
	raise e

print 'Logging sensor measurements every {0} seconds.'.format(FREQUENCY_SECONDS)
print 'Press Ctrl-C to quit.'

while True:
	
	# Attempt to get sensor reading.
	retries = 0;
	success = False
	while (retries < READING_RETRIES) and not success:

		# humi, temp = Adafruit_DHT.read(DHT_TYPE, DHT_PIN)
		humi = 10
		temp = 01
		timeNow = datetime.datetime.now()

		if temp is None:
			retries += 1
			time.sleep(2)
		else:
			success = True

	# Print the current reading
	if success:
		print (timeNow)
		print 'Temperature: {0:0.1f} C'.format(temp)
		print 'Humidity:    {0:0.1f} %'.format(humi)

		# Store the results
		timeData.append(timeNow)
		tempData.append(temp)
		humiData.append(humi)

	else:
		print (timeNow)
		print 'Temperature reading failed'

	# Remove any out dated results
	delIdxs = []
	for idx, t in enumerate(timeData):
		dt = timeNow - t
		if (dt.total_seconds()/3600 > HISTORY_LENGTH):
			delIdxs.append(idx)

	# Delete all the entries up to the out of date one
	if len(delIdxs) > 0:
		print('Deleting old entries')
		maxIdx = max(delIdxs)
		del(timeData[0:maxIdx])
		del(tempData[0:maxIdx])
		del(humiData[0:maxIdx])

	# Update the csv file
	dataFile = open(DATA_FILENAME,'wb')
	dataWriter = csv.writer(dataFile)
	for idx, data in enumerate(timeData):
		dataWriter.writerow((timeData[idx],tempData[idx],humiData[idx]))
	dataFile.close()

	dataFile = open(DATA_FILENAME,'r')
	# Upload via ftp
	ftp.storbinary('STOR /cutsquash.com/data.csv', dataFile);

	# Done with the data file
	dataFile.close()

	# If there were problems try and fix them
 	
	# Wait until the next reading
	time.sleep(FREQUENCY_SECONDS)
