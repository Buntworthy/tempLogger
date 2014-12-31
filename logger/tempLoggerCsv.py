#!/usr/bin/python

################## TEMP LOGGING ##################
#
# Temperature logging to csv file on RPi
#
# Logs the temperature, humidity and time of the
# measurement into 3 csv log files:
# data24h.csv 
#		- 1 measurement per min for 24 hours
# data7d
# 		- 1 measurement per 10 mins for 7 days
# data30d
#		- Min/max per day for 30 days
#
##################################################

import sys
import time
import datetime
import csv
import numpy as np
from ftplib import FTP

import Adafruit_DHT

################### Fucntions ###################

def readData(filename):

	# Create measurement variables
	timeData = []
	tempData = []
	humiData = []

	# Read in the existing data if it is there
	dataFile = open(filename,'rb')
	dataReader = csv.reader(dataFile)
	next(dataReader) # skip the first row
	for row in dataReader:
		# load time
		loadTime = datetime.datetime.strptime(
			row[0],
			'%Y-%m-%d %H:%M:%S.%f')

		timeData.append(loadTime)
		tempData.append(row[1])
		humiData.append(row[2])

	dataFile.close()

	return (timeData, tempData, humiData)

def storeResults((timeNow, temp, humi),(timeData,tempData,humiData)):

	# Store the results
	timeData.append(timeNow)
	tempData.append(temp)
	humiData.append(humi)

	return (timeData,tempData,humiData)

def removeOldResults((timeData, tempData, humiData), HISTORY_LENGTH, timeNow):

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

	return (timeData, tempData, humiData)

def updateCsv((timeData, tempData, humiData), DATA_FILENAME):

	# Update the csv file
	dataFile = open(DATA_FILENAME,'wb')
	dataWriter = csv.writer(dataFile)
	# Write the headers
	dataWriter.writerow(('Time','Temperature','Humidity'))
	for idx, data in enumerate(timeData):
		dataWriter.writerow((timeData[idx],tempData[idx],humiData[idx]))
	dataFile.close()

def updateCsvMM((timeData, tempData, humiData), DATA_FILENAME):

	# Update the csv file
	dataFile = open(DATA_FILENAME,'wb')
	dataWriter = csv.writer(dataFile)
	# Write the headers
	dataWriter.writerow(('Time','Min','Max'))
	for idx, data in enumerate(timeData):
		dataWriter.writerow((timeData[idx],tempData[idx],humiData[idx]))
	dataFile.close()

def uploadFtp((timeData, tempData, humiData), DATA_FILENAME, ftp, user, pword):

	# Upload via ftp
	dataFile = open(DATA_FILENAME,'r')
	try:
		ftp.storbinary('STOR /cutsquash.com/' + DATA_FILENAME, dataFile);
		print('Uploaded to ftp')

	except Exception, e:
		print('Could not upload the file to ftp')
		time.sleep(10)
		# Reconnect to ftp
		print('Attempting to reconnect')
		ftp.connect()
		ftp.login(user, pword)
		print('Logged back in')

	# Done with the data file
	dataFile.close()

################ Program constants ################

# Sensor details
DHT_TYPE = Adafruit_DHT.DHT22
DHT_PIN  = 4

# Sampling frequency.
FREQUENCY_SECONDS = 5
SAMPLING_24 = 60
SAMPLING_7 = 10*60

# How many times to retry any reading
READING_RETRIES = 5

# Filenames
SETTINGS_FILENAME = 'config.csv'
DATA_FILENAME_24  = 'data24.csv'
DATA_FILENAME_7   = 'data7.csv'
DATA_FILENAME_MM   = 'dataMinMax.csv'

# How much data to store (hours)
HISTORY_LENGTH_24 = 24
HISTORY_LENGTH_7  = 7*24
HISTORY_LENGTH_MM  = 30*7*24

###################################################

prevReadingTime24 = datetime.datetime.now()
prevReadingTime7 = datetime.datetime.now()
prevReadingTimeMinMax = datetime.datetime.now()

(timeData24, tempData24, humiData24) = readData(DATA_FILENAME_24)
(timeData7, tempData7, humiData7) = readData(DATA_FILENAME_7)
(timeDataMM, minDataMM, maxDataMM) = readData(DATA_FILENAME_MM)

# Load the FTP access details
configFile = open(SETTINGS_FILENAME,'rb')
configReader = csv.reader(configFile)
config = {rows[0]:rows[1] for rows in configReader}
host = config['host']
user = config['user']
pword = config['pword']

# Set up FTP access object
ftp = FTP(host, timeout = 30)
try:
	print('Logging into ftp server ' + host)
	ftp.login(user, pword)

except Exception, e:
	print('Failed to log into FTP server')
	raise e

print 'Logging sensor measurements every {0} seconds.'.format(FREQUENCY_SECONDS)
print 'Press Ctrl-C to quit.'

while True:

	# Check the time to see if we need a new reading
	timeCheck = datetime.datetime.now()
	update24 = False
	update7 = False
	updateMinMax = False

	if (timeCheck - prevReadingTime24).total_seconds() > SAMPLING_24:
		update24 = True
		prevReadingTime24 = timeCheck
		print('Updating 24 hour data')

	if (timeCheck - prevReadingTime7).total_seconds() > SAMPLING_7:
		update7 = True
		prevReadingTime7 = timeCheck
		print('Updating 7 day data')

	# Check if we have crossed to a new day and need to update the minmax value
	if (timeCheck.toordinal() > prevReadingTimeMinMax.toordinal()):
		updateMinMax = True
		prevReadingTimeMinMax = timeCheck
		print('Updating MinMax data')

	if update24:
		
		# Attempt to get sensor reading.
		retries = 0;
		success = False
		while (retries < READING_RETRIES) and not success:

			humi, temp = Adafruit_DHT.read(DHT_TYPE, DHT_PIN)
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

			if update24:
				# Add new results
				(timeData24, tempData24, humiData24) = storeResults((timeNow, temp, humi),
														(timeData24, tempData24, humiData24))
				# Remove old results
				removeOldResults((timeData24, tempData24, humiData24), HISTORY_LENGTH_24, timeNow)

				# Update csv file
				updateCsv((timeData24, tempData24, humiData24), DATA_FILENAME_24)

				# Upload via ftp
				uploadFtp((timeData24, tempData24, humiData24), DATA_FILENAME_24, ftp, user, pword)

		else:
			print (timeNow)
			print 'Temperature reading failed'

	if update7:

		# Take the average of the past period of data
		nSamples = np.floor(SAMPLING_7/SAMPLING_24)

		# Make sure this isn't longer than the length of the 24 hour data
		nSamples = min(nSamples, len(tempData24))

		temp = np.mean(tempData24[-int(nSamples):])
		humi = np.mean(humiData24[-int(nSamples):])

		# Add new results
		(timeData7, tempData7, humiData7) = storeResults((timeNow, temp, humi),
												(timeData7, tempData7, humiData7))
		# Remove old results
		removeOldResults((timeData7, tempData7, humiData7), HISTORY_LENGTH_7, timeNow)

		# Update csv file
		updateCsv((timeData7, tempData7, humiData7), DATA_FILENAME_7)

		# Upload via ftp
		uploadFtp((timeData7, tempData7, humiData7), DATA_FILENAME_7, ftp, user, pword)

	if updateMinMax:
		# Update the min max data and files
		# Take the min and max of the past 24 hours
		
		tempMin = min(tempData24)
		tempMax = max(humiData24)

		# Add new results
		(timeDataMM, minDataMM, maxDataMM) = storeResults((timeNow, tempMin, tempMax),
												(timeDataMM, minDataMM, maxDataMM))
		# Remove old results
		removeOldResults((timeDataMM, minDataMM, maxDataMM), HISTORY_LENGTH_MM, timeNow)

		# Update csv file
		updateCsvMM((timeDataMM, minDataMM, maxDataMM), DATA_FILENAME_MM)

		# Upload via ftp
		uploadFtp((timeDataMM, minDataMM, maxDataMM), DATA_FILENAME_MM, ftp, user, pword)

	# Wait until the next reading
	time.sleep(FREQUENCY_SECONDS)
