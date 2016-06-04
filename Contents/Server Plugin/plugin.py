#! /usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Michael Hesketh - Corporate Chameleon Limited'
############################################################################################
# Copyright (c) 2015, Corporate Chameleon Limited. All rights reserved.
# http://www.corporatechameleon.co.uk
#
# This plugin is designed to manage multiple iPhone devices initially as location aids for Indigo
# Additional functionality will be added for security and other iCloud Functions
#
# It relies on pyicloud, requests and six for managing the iPhone iCloud API.  With the addition of
# family groups there is now the opportunity to provide location information on all related equipment
# The installation of these dependencies is covered in the readme.txt file
# That is distributed with this script
# Instructions on how to do this are contained in the README.txt file on the Indigo Support Site
# Thanks to all the people who suffered the Alpha phase:
#
# Without their testing and great ideas we wouldn't have even reached the Alpha stage!
#
# This software is provided 'as-is' and may contain bugs at this point
# Use of this software is the responsibility of the user and no claims
# will be accepted for any damage or expenses relating to its use.
#
# This version includes a link between NEST Home and iFindStuff and FINGScan and iFindStuff
# Special thanks to - Karl Wachs (author of many great plugins) for his support in linking this to
# FINGScan and spotting some really hidden bugs - greatly appreciated :D
#
# Version:      1.01.01 (Production release iFindStuff)
# API Version:  1.9
# Author:       Mike Hesketh
# Released:     23rd Sept 2015
#
# Requirements: Indigo 6.1/API 1.19 or greater
#               Python 2.6 or greater (not tested with Python 3)
#               Internet access
#               Standard python libraries
#               REQUESTS and SIX libraries are also required
#
# This code may be freely distributed and used but copyright references must included
# Use of the Apple iCloud API is managed Apple and the code remains their property
# Use of Google Maps API is managed by Google and the code remains their property
# but they both allow free commercial & personal use as long as the user agrees to their
# Terms of Service.
# These terms can be viewed at http://apple.com
#
############################################################################################

# Check environment for indigo and pyicloud
import sys
import os

# Set up the relative path
# Although this should work with ./directory it doesn't if the user has not got the
# script in the same directory as the working directory.  This method is more robust

pypath = os.path.realpath(sys.path[0])
sys.path.append(pypath)

# First check that we're in Indigo!
try:
    import indigo
except:
    print("This programme must be run from inside Indigo Pro 6.1")
    sys.exit(0)

# Now the iCloud libraries.  These are self contained in the package as they have been adjusted to allow
# Access to the Apple Find my Phone API without constant 'Security emails'

try:
    from pyicloud import PyiCloudService
    from pyicloud.exceptions import PyiCloudFailedLoginException

except:
    indigo.server.log("FATAL ERROR - Cannot find pyicloud - check with developer")
    indigo.server.log("Most probable error is pytz is not installed on your system. Read the forum for post on "
                      "Can't find pyicloud for more details and how to resolve."
                      "Alternatively - check the name of the plugin in the Plugins folder.  Is is iFindStuff.pluginIndigo"
                      "or iFindStuff(1).pluginIndigo?  Make sure that all iFindStuff files are deleted from Downloads"
                      "before downloading the latest versions")

# Now the HTTP and Compatibility libraries
try:
    import six
    import requests

except:
    indigo.server.log("Note: requests.py and six.py must be installed for this plugin to operate.  See the forum")
    indigo.server.log("Alternatively - check the name of the plugin in the Plugins folder.  Is is iFindStuff.pluginIndigo"
                      "or iFindStuff(1).pluginIndigo?  Make sure that all iFindStuff files are deleted from Downloads"
                      "before downloading the latest versions")


# Now the html mapping libraries - note that these have also been modified to allow custom icons
try:
    from pygmaps.pygmaps import maps
except:
    indigo.server.log("pygmaps.py error - No Map functionality availiable - contact Developer")

# Date and time libraries
import time

# Now install GeoCoder for reverse address lookup
from pygeocoder import Geocoder, GeocoderError, GeocoderResult

# Now install TinyDB
from tinydb import TinyDB, where

try:
    import indigoPluginUpdateChecker

except ImportError:
    indigo.server.log('No update checker installed')
    sys.exit(0)

# Now import the standard python 2.6 libraries that are used
import math
import webbrowser
import datetime
from googlemaps import googlemaps
import traceback

# Finally switch off warnings on SSL access
requests.packages.urllib3.disable_warnings()

##############################
# USER DEFINED FUNCTIONS
#################

global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, iDebug5, iDebug6

# Set up Global fields and directories
global gNumFields
global addAccountId
global gtempKeys
global gCurrentAccount
global gAppleAPI
global gUnits
global gIcon
global gAccountMasterDict
global fingScanLink
global iTrackHistory
global db
global errorFile

gTempKeys = {}
gNumFields = 2
addAccountId=0
gCurrentAccount = 0
gAppleAPI = 0
gUnits = "Metres"
gAccountMasterDict = {}

iDebug1 = False
iDebug2 = False
iDebug3 = False
iDebug4 = False
iDebug5 = False
iDebug6 = True
iTrackHistory = True
fingScanLink = False
errorFile = '/Library/Application Support/Perceptive Automation/Indigo 6/Logs/iFindStuffErrors.log'

def errorHandler(myError):
    global iDebug6, errorFile

    if iDebug6:
        f = open(errorFile,'a')
        f.write('-'*80+'\n')
        f.write('Exception Logged:'+str(time.strftime(time.asctime()))+' in '+myError+' module'+'\n\n')
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=f)
        f.write('-'*80+'\n')
        f.close()

def setupAPI():
    ################################################
    # Sets up the Apple API Fields for the programme
    # Check API

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
    if iDebug3:
        indigo.server.log(u'Setting up the API...')
    try:
        # Set up the API
        iCloudAPIStatus=[]
        iCloudAPILocation = []

        # Status first
        iCloudAPIStatus.append('deviceDisplayName')
        iCloudAPIStatus.append('deviceStatus')
        iCloudAPIStatus.append('batteryLevel')
        iCloudAPIStatus.append('name')
        iCloudAPIStatus.append('deviceModel')
        iCloudAPIStatus.append('locationEnabled')
        iCloudAPIStatus.append('isLocating')
        iCloudAPIStatus.append('batteryStatus')
        iCloudAPIStatus.append('isMac')

        allStatusFields = []
        for lines in range(len(iCloudAPIStatus)):
            allStatusFields.append(iCloudAPIStatus[lines])

        # Now Location
        iCloudAPILocation.append('timeStamp')
        iCloudAPILocation.append('positionType')
        iCloudAPILocation.append('horizontalAccuracy')
        iCloudAPILocation.append('longitude')
        iCloudAPILocation.append('latitude')
        iCloudAPILocation.append('isOld')
        iCloudAPILocation.append('isInaccurate')

        allLocationFields = []
        for lines in range(len(iCloudAPILocation)):
            allLocationFields.append(iCloudAPILocation[lines])

        if iDebug3:
            indigo.server.log(u'Standard API fields set up correctly...')

        return iCloudAPIStatus, iCloudAPILocation, allStatusFields, allLocationFields

    except:
        # Problems setting up the API
        errorHandler('Standard API')
        if iDebug1:
            indigo.server.log(u'Problems setting up the Standard API...')

def iCustomAPI():
    ################################################
    # Sets up the Custom State fields for programme reference

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

    if iDebug1:
        indigo.server.log(u'Setting up the Custom API...')

    try:
        iStates = []
        iStates.append("deviceUniqueKey")
        iStates.append("deviceDisplayName")
        iStates.append("deviceStatus")
        iStates.append("deviceBattery")
        iStates.append("deviceName")
        iStates.append("deviceModel")
        iStates.append("deviceLocationEnabled")
        iStates.append("deviceIsLocating")
        iStates.append("batteryOnCharge")
        iStates.append("deviceIsMac")
        iStates.append("deviceTimeChecked")
        iStates.append("devicePositionType")
        iStates.append("deviceAccuracy")
        iStates.append("deviceLongitude")
        iStates.append("deviceLatitude")
        iStates.append("deviceIsOldPosition")
        iStates.append("deviceInaccurate")



        if iDebug3:
                indigo.server.log(u'Custom API fields set up correctly...')

    except:
        errorHandler('Custom API')
        # Problems setting up the custom API

        if iDebug1:
            indigo.server.log(u'Problems setting up the Custom API...')

    return iStates

def createAccountMaster(accountId):
    ################################################
    # Routine creates an Account Master device and
    # validates the login details before storing.  If in error
    # it stops the user progressing through an error

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, gAccountMasterDict

    try:
        acc = indigo.devices[int(accountId)]
        gAccountMasterDict = {}
        iaProps = acc.pluginProps
        if iDebug3:
            indigo.server.log('Creating directory for account:'+acc.name)

        iLogin = iAuthorise(iaProps['appleId'], iaProps['applePwd'])

        if not iLogin[0] == 0:
            # Failed login
            if iDebug1:
                indigo.server.log("Could not log in with username/password combination")

            return False, gAccountMasterDict

        else:
            iAccountNumber = str(acc.id)
            api = iLogin[1]
            iAccountDevices = api.devices
            iAccountKeys = iAccountDevices.keys()
            iAccountList = {}
            for iCode in iAccountKeys:
                iFound = False
                for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                    if dev.states['deviceUniqueKey'] == iCode:
                        iFound = True
                        break

                # Remove any odd characters from the name

                if type(iAccountDevices[iCode]['name']) == unicode:

                    # Check for semi colons, colons and , and replace then with spaces
                    checkString = iAccountDevices[iCode]['name']
                    checkString = checkString.replace(',',' ')
                    checkString = checkString.replace(':',' ')
                    checkString = checkString.replace(';',' ')
                    checkString = checkString.replace("'","")

                    iAccountList[iCode] = checkString, iFound

                else:
                    iAccountList[iCode] = iAccountDevices[iCode]['name'], iFound

            # Now store all the keys in the Account Directory
            gAccountMasterDict[iAccountNumber] = iAccountList
            if iDebug3:
                indigo.server.log('Directory is now:'+str(gAccountMasterDict))

        # Devices added to Dictionary so return OK
        return True, gAccountMasterDict

    except:
        errorHandler('createAppleAccount ')
        return

def iAuthorise(iUsername, iPassword):
    ################################################
    # Logs in and authorises access to the Find my Phone API

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

    # Logs into the find my phone API and returns an error if it doesn't work correctly
    if iDebug3:
        indigo.server.log(u'Attempting login...')

    # Logs into the API as required
    try:
        appleAPI = PyiCloudService(iUsername, iPassword)

        if iDebug3:
            indigo.server.log(u'Login successful...')
        return 0, appleAPI

    except PyiCloudFailedLoginException:
        errorHandler('iAuthorise')
        indigo.server.log(u'Login failed - Check username/password - has it changed recently?...', type="iFindStuff Critical ", isError=True)
        return 1,'NL'

    except:
        errorHandler('Internet Connection Down')
        indigo.server.log(u'Login failed - Check your internet connection...', type="iFindStuff Urgent ", isError=True)
        return 1,'NI'

def iMapping(iUsername, iPassword, iAccountName, iAccountId, iDevName, iDevKey, iDevId):

    ################################################
    # Maps all of the devices contained in an account including Family devices

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
    global gNumFields
    global gCurrentAccount
    global gAppleAPI
    iDeviceDict = {}

    # Finds the device attached to an account
    if iDebug3:
        indigo.server.log(u'Refreshing Apple Device...'+str(iDevName)+' on account '+ iAccountName)

    try:
        # First set up the APIs
        mapAPI = setupAPI()
        iCloudAPIStatus = mapAPI[0]
        iCloudAPILocation = mapAPI[1]
        allStatusFields = mapAPI[2]
        allLocationFields = mapAPI[3]

        # Check if we need to login
        if gCurrentAccount != iAccountId:
            # Account has changed so we need to login
            iLogin = iAuthorise(iUsername, iPassword)

            gCurrentAccount = iAccountId

            if not iLogin[0] == 0:
                # Failed to login
                if iLogin[1] == 'NL':
                    return 1, 'NL'
                else:
                    return 1, 'NI'
            else:
                gAppleAPI = iLogin[1]

        # Logged in so now get the information we need
        # Store API reference
        appleAPI = gAppleAPI

        # This is completed for each device individually
        # Get the data and convert it and place in an array
        iInformation = []

        # Get the data for that key only
        try:
            # Update - we only need to call the API once for all the data
            iAllData = appleAPI.devices[iDevKey].data

            # Now extract the information for Status
            iStatus = {}
            for iStatusValue in range(len(allStatusFields)):

                # Remove any odd characters from the information
                if type(iAllData[allStatusFields[iStatusValue]]) == unicode:
                    # Check for semi colons, colons and , and replace then with spaces
                    checkString = iAllData[allStatusFields[iStatusValue]]
                    checkString = checkString.replace(',',' ')
                    checkString = checkString.replace(':',' ')
                    checkString = checkString.replace(';',' ')
                    checkString = checkString.replace("'","")
                    iStatus[allStatusFields[iStatusValue]] = checkString
                else:
                    # Now store the field
                    iStatus[allStatusFields[iStatusValue]] = iAllData[allStatusFields[iStatusValue]]

            # Now the information for Location
            iLocation = appleAPI.devices[iDevKey].data['location']

        except KeyError:
            errorHandler('iMapping'+iDevName)
            if iDebug2:
                indigo.server.log('P3E')
                indigo.server.log('Device'+iDevName+' '+iDevKey)
            return 1, 'DM'

        except:
            errorHandler('iMapping'+iDevName)
            if iDebug2:
                if iDebug2:
                    indigo.server.log('NCE')
                    indigo.server.log('Device'+iDevName+' '+iDevKey)
            return 1, 'NCE'


        iMap = {}

        try:
            iStatusFields = []

            # Get data
            if iStatus != None:

                #Store the unique device key
                iStatusFields.append(iDevKey)

                # Now the data
                iBattStat = 'Not Read'
                iDeviceIsMac = 'Unknown'

                for iAPIStat in iCloudAPIStatus:
                    try:
                        if iAPIStat == 'batteryStatus':
                            iBattStat = iStatus[iAPIStat]

                        if iAPIStat == 'deviceIsMac':
                            iDeviceIsMac = 'isMacFound'
                            iDeviceMac = iStatus[iAPIStat]

                        if iBattStat != 'Not Read' and iDeviceIsMac != 'Unknown':
                            # Both trapped fields seen have now been read so check

                            if iBattStat == 'Unknown' and not iDeviceMac:
                                # Phone wasn't read on last occasion - it's offline
                                dev = indigo.devices[iDevId]
                                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                                if iDebug1:
                                    indigo.server.log('Phone offline or could not be read:'+dev.name)

                                return 2,'NR'

                        iStatusFields.append(iStatus[iAPIStat])
                        # Check if we were able to get to the device on this occasion


                    except:
                        errorHandler('iMapping '+str(iAPIStat))
                        if iDebug2:
                            indigo.server.log(u'Problems setting a Status API field')
                            indigo.server.log(u'Location API Field:'+str(iAPIStat))

                dev = indigo.devices[iDevId]
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

            else:
                if iDebug2:
                    indigo.server.log(u'Warning - No Status information:'+str(iDevName)+u' Device is probably '
                                                                                         u'inactive')
                iStatusFields.append('** No Status Information Found **')

            if iLocation != None:
                # Now the location information

                for iAPILoc in iCloudAPILocation:
                    try:
                        iStatusFields.append(iLocation[iAPILoc])

                    except:
                        errorHandler('iMapping '+ str(iAPILoc))
                        if iDebug2:
                            indigo.server.log(u'Problems setting a Location API field')
                            indigo.server.log(u'Location API Field:'+str(iAPILoc))

            else:
                if iDebug2:
                    indigo.server.log(u'Warning - No Location information:'+str(iDevKey)+u' Device is '
                                                                                           u'probably inactive')
                iStatusFields.append('** No Location Data Found **')

            if iDebug3:
                indigo.server.log(u'Updating status map for device')
                indigo.server.log(u'Contents are:'+str(iStatusFields))

        except:
            errorHandler('iMapping '+iDevName)
            if iDebug1:
                indigo.server.log(u"Failed to extract information for device:"+str(iDevName))
    except:
        errorHandler('iMapping - GF0')
        if iDebug1:
            indigo.server.log(u"Code failure on extracting information - advise Developer")
        return 1, 'GF0'

    # Ok now we need to extract the data we've collected and then convert it ready to update the devices
    # Reserve some analysis space
    if iDebug3:
        indigo.server.log(u'Converting and storing custom states for devices...')

    try:
        # Check device in turn
        if iDebug3:
            indigo.server.log(u'Refreshing Device:'+str(iDevName))

        # iPhones first
        iDevData = iStatusFields

        if iDebug3:
            indigo.server.log(u'Conversion field details for device:'+str(iDevName))
            indigo.server.log(u'Battery:'+str(iDevData[3]))
            indigo.server.log(u'TimeStamp:'+str(iDevData[10]))

        for iData in range(len(iDevData)):
            if iData == 3: # Battery Level
                iTempData = iTempData+','+str(int(iDevData[3]*100))+'%'

            elif iData == 10: # Time Stamp in ms
                if type(iDevData[10]) == long:
                    if iDebug3:
                        indigo.server.log('TimeStamp on device:'+str(iDevName)+' '+str(int(iDevData[10]/1000.0)))

                    iTime = time.asctime(time.localtime(int(iDevData[10]/1000.0)))
                    iTempData = iTempData+','+iTime
                else:
                    if iDebug2:
                        indigo.server.log(u'Warning - Time Stamp is absent for iDevice:'+str(iDevName)
                                          +u' iPhone is probably inactive')

                    iTempData = iTempData+','+"** No Timestamp **"
                    iTempData = iTempData+','+"None"
                    iTempData = iTempData+','+"0.0"
                    iTempData = iTempData+','+"0"
                    iTempData = iTempData+','+"0"
                    iTempData = iTempData+','+"True"
                    iTempData = iTempData+','+"True"
            else:
                try:
                    if iData != 0:
                        iTempData = iTempData+','+str(iDevData[iData].encode('ascii', 'ignore'))
                    else:
                        iTempData = str(iDevData[iData].encode('ascii', 'ignore'))

                except:
                    if iData != 0:
                        iTempData = iTempData+','+str(iDevData[iData]).encode('ascii', 'ignore')
                    else:
                        iTempData = iDevData[iData].encode('ascii', 'ignore')

        # Store the result
        iInformation.append(iTempData)

    except:
        errorHandler('iMapping - GF1')
        if iDebug2:
            indigo.server.log(u'Critical - Failed to convert data from API - raise to Developer')

        return 1, "GF1"

    # We can build the data dictionary for the device
    try:
        if iDebug3:
            indigo.server.log(u'Converting data before return...')

        # Convert to a list
        iDeviceInformation = []
        for deviceNumber in range(len(iInformation)):
            iDeviceInformation.append(iInformation[deviceNumber].split(','))

        iDeviceDict = {}
        iDeviceData = {}
        iCustStates = iCustomAPI()

        iDeviceInformation = []
        for deviceNumber in range(len(iInformation)):
            iDeviceInformation.append(iInformation[deviceNumber].split(','))

        for iItem in range(len(iDeviceInformation)):
            for iField in range(len(iCustStates)):
                iDeviceData[iCustStates[iField]] = iDeviceInformation[iItem][iField]

            iDeviceDict['Phablet '+str(iItem+1)] = iDeviceData
            iDeviceData = {}

        if iDebug3:
            indigo.server.log(u'Data converted successfully...')

        # Now refresh the device information
        iRefresh = iRefreshDevices(iDeviceDict, iDevId)
        if iRefresh[0] == 0:
            if iDebug3:
                indigo.server.log('Good Refresh...')
            return 0,"OK"
        else:
            if iDebug3:
                indigo.server.log('Poor Refresh...')
            return 1, iRefresh[1]

    except:
        errorHandler('iMapping - GF2')
        if iDebug1:
            indigo.server.log(u'Data conversion to list iDeviceDict failed...')
            return 1, 'GF2'

    return 0,"OK"

def iRefreshDevices(iDeviceDict, iDevId=0):

    ################################################
    # Refreshes a single devices assigned to iFindStuff
    # Note it must have been created first

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, iDebug5

    # Can only be called once iMapping is completed
    # iDeviceInformation contains all of the latest iDevice data

    if iDeviceDict == {}:
        # No iDevice found

        if iDebug1:
            indigo.server.log(u'iDevices refresh - Terminal error no devices found - no devices found after mapping')

        return 1, 'ND'

    # Set up update fields
    iAPI = setupAPI()
    iStates = iCustomAPI()

    # Collect device for refresh
    dev = indigo.devices[iDevId]

    try:
        if iDebug3:
            indigo.server.log(u'Converting:'+str(dev.name))

        if not (dev.enabled and dev.configured):
            if iDebug1:
                indigo.server.log(u'Device '+dev.name+u' is not configured or enabled in Indigo')

            return 1, 'NC'

        iDeviceKey = dev.states['deviceUniqueKey']

        # Is device in the dictionary?
        # Set not found flag
        iFound = False

        for iDevice in range(len(iDeviceDict.keys())):
            # Looking for the device in the keys
            if iDeviceKey == iDeviceDict['Phablet '+str(iDevice+1)]['deviceUniqueKey']:
                if iDebug2:
                    indigo.server.log('Matching Phablet Number:'+ str(iDevice))

                # Found it!
                iFound = True
                break

            if iDebug3:
                indigo.server.log(u'iDevice processed:'+str(iDevice))

        # if iFound is True then we update it
        if iFound == True:
            iUpdate = updateDevice(dev, iDeviceDict, iStates, 'Phablet '+str(iDevice+1))

            if not iUpdate[0]:
                # Problems on update
                return 1, "UF"

        else:
            if iDebug2:
                indigo.server.log(u'No matching device for:'+str(iDeviceKey)+u" - contact Developer")

    except:
        errorHandler('refreshDevices '+dev.name)
        if iDebug1:
            indigo.server.log(u'Warning: Failed to process:'+ dev.name)
        pass
        return 1, 'PX'

    return 0, 'OK'

def iAccountOnline(iUsername, iPassword, acc):

    ################################################
    # Used in configuration to review all active devices against an account
    # regardless of whether they are assigned or not

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
    global gCurrentAccount
    global gAppleAPI

    # Downloads the current iDevice Map for both Phones and Tablets
    # As well as all of the current data for parsing

    iDeviceDict = {}

    if iDebug3:
        indigo.server.log(u'Refreshing iDevices map from Apple API...')

    try:

        if iDebug3:
            iDebug2Username = iUsername
            iDebug2Username = iDebug2Username[:6]+"..."+iDebug2Username[-4:]
            indigo.server.log(u'Attempting to map active account ('+iDebug2Username+')...')

        # First set up the APIs
        mapAPI = setupAPI()
        iCloudAPIStatus = mapAPI[0]
        iCloudAPILocation = mapAPI[1]
        allStatusFields = mapAPI[2]
        allLocationFields = mapAPI[3]
        iAccountId = acc.id
        iAccountName = acc.name

        # Check if we need to login

        if gCurrentAccount != iAccountId:
            # Account has changed so we need to login
            iLogin = iAuthorise(iUsername, iPassword)

            gCurrentAccount = iAccountId

            if not iLogin[0] == 0:
                # Failed to login
                if iLogin[1] == 'NL':
                    # Failed to login using credentials
                    indigo.server.log(u'Failed login.  To avoid lockout on the account iFindStuff will try once more before'
                                      u'terminating. Please update/check internet connection or login details before restart',
                                      type='iFindStuff Critical', isError = True)
                    return 1,"NL"
                else:
                    return 1, 'NI'
            else:
                gAppleAPI = iLogin[1]

        # Logged in so now get the information we need
        appleAPI = gAppleAPI
        iDevices = appleAPI.devices
        iMap = {}
        iStatusFields = []
        iNumberOfDevices = len(iDevices.keys())

        # Start by identifing the total number of devices for analysis
        if iDebug3:
            indigo.server.log(u'Keys found in the current Apple Account...')
            indigo.server.log(str(iDevices.keys()))

        if iDebug3:
            indigo.server.log(u"Number of devices found:"+str(iNumberOfDevices))


        # Now extract information for each device in turn
        for iDeviceId in range(len(iDevices.keys())):
            try:
                # Update - we only need to call the API once for all the data
                iAllData = appleAPI.devices[iDeviceId].data

                # Now extract the information for Status
                iStatus = {}
                for iStatusValue in range(len(allStatusFields)):

                    # Remove any odd characters from the information

                    if type(iAllData[allStatusFields[iStatusValue]]) == unicode:
                        # Check for semi colons, colons and , and replace then with spaces
                        checkString = iAllData[allStatusFields[iStatusValue]]
                        checkString = checkString.replace(',',' ')
                        checkString = checkString.replace(':',' ')
                        checkString = checkString.replace(';',' ')
                        checkString = checkString.replace("'","")
                        iStatus[allStatusFields[iStatusValue]] = checkString
                    else:
                        iStatus[allStatusFields[iStatusValue]] = iAllData[allStatusFields[iStatusValue]]

                    iStatus[allStatusFields[iStatusValue]] = iAllData[allStatusFields[iStatusValue]]

                # Now the information for Location
                iLocation = appleAPI.devices[iDeviceId].data['location']

                if iStatus != None:

                    #Store the unique device key
                    iStatusFields.append(iDevices.keys()[iDeviceId])

                    # Now the data
                    for iAPIStat in iCloudAPIStatus:
                        try:
                            iStatusFields.append(iStatus[iAPIStat])
                        except:
                            errorHandler('iAccount')
                            if iDebug2:
                                indigo.server.log(u'Problems setting a Status API field')
                                indigo.server.log(u'Location API Field:'+str(iAPILoc))
                                indigo.server.log(u'Location API Field Value:'+str(iLocation[iAPILoc]))

                else:
                    if iDebug2:
                        indigo.server.log(u'Warning - No Status information:'+str(iDeviceId)+u' Device is probably '
                                                                                             u'inactive')
                    iStatusFields.append('** No Status Information Found **')

                if iLocation != None:
                    # Now the location information
                    for iAPILoc in iCloudAPILocation:
                        try:
                            iStatusFields.append(iLocation[iAPILoc])
                        except:
                            errorHandler('iAccount')
                            if iDebug2:
                                indigo.server.log(u'Problems setting a Location API field')
                                indigo.server.log(u'Location API Field:'+str(iAPILoc))
                                indigo.server.log(u'Location API Field Value:'+str(iLocation[iAPILoc]))

                else:
                    if iDebug2:
                        indigo.server.log(u'Warning - No Location information:'+str(iDeviceId)+u' Device is '
                                                                                               u'probably inactive')
                    iStatusFields.append('** No Location Data Found **')

                iMap['Phablet '+str(iDeviceId)] = iStatusFields
                iStatusFields =[]

                if iDebug3:
                    indigo.server.log(u'Updating status map for device')
                    indigo.server.log(u'Contents are:'+str(iStatusFields))
            except:
                errorHandler('iAccount '+str(iDeviceId))
                if iDebug2:
                    indigo.server.log(u"Failed to extract information for device:"+str(iDeviceId))

                return False, {}

        # Ok now we need to extract the data we've collected and then convert it ready to update the devices
        # Reserve some analysis space
        if iDebug3:
            indigo.server.log(u'Converting and storing custom states for devices...')

        try:
            iPhones = []
            iTablets = []
            iNumberOfDevices = len(iMap.keys())

            # Check each device in turn
            for iDeviceId in range(iNumberOfDevices):
                # What type of device are we thinking of?
                if iMap['Phablet '+str(iDeviceId)][1].find('Phone') != -1:
                    # It's a phone
                    iPhones.append(str(iMap['Phablet '+str(iDeviceId)]))

                    if iDebug3:
                        indigo.server.log(u'Added iPhone Device:'+str(iDeviceId))

                elif iMap['Phablet '+str(iDeviceId)][1].find('Pad') != -1:
                    # It's an iPad
                    iTablets.append(str(iMap['Phablet '+str(iDeviceId)]))

                    if iDebug3:
                        indigo.server.log(u'Added iTablet Device:'+str(iDeviceId))

                elif iMap['Phablet '+str(iDeviceId)][9]:
                    # Its a MAC
                    iTablets.append(str(iMap['Phablet '+str(iDeviceId)]))

                    if iDebug3:
                        indigo.server.log(u'Added iTablet Device:'+str(iDeviceId))

            # Convert the data held and place in an array
            iInformation = []

            # iPhones first
            if len(iPhones)>0:
                for iPhoneDevices in range(len(iPhones)):
                    iTempData = ''
                    iDevData = eval(iPhones[iPhoneDevices])

                    if iDebug3:
                        indigo.server.log(u'Conversion field details for iPhone:'+str(iPhoneDevices))
                        indigo.server.log(u'Battery:'+str(iDevData[3]))
                        indigo.server.log(u'TimeStamp:'+str(iDevData[10]))

                    for iData in range(len(iDevData)):
                        if iData == 3: # Battery Level
                            iTempData = iTempData+','+str(int(iDevData[3]*100))+'%'

                        elif iData == 10: # Time Stamp in ms
                            if type(iDevData[10]) == long:
                                iTime = time.asctime(time.localtime(int(iDevData[10]/1000.0)))
                                iTempData = iTempData+','+iTime
                            else:
                                if iDebug2:
                                    indigo.server.log(u'Warning - Time Stamp is absent for iPhone:'+str(iPhoneDevices)
                                                      +u' iPhone is probably inactive')

                                iTempData = iTempData+','+"** No Timestamp **"
                                iTempData = iTempData+','+"None"
                                iTempData = iTempData+','+"0.0"
                                iTempData = iTempData+','+"0"
                                iTempData = iTempData+','+"0"
                                iTempData = iTempData+','+"True"
                                iTempData = iTempData+','+"True"
                        else:
                            try:
                                if iData != 0:
                                    iTempData = iTempData+','+str(iDevData[iData].encode('ascii', 'ignore'))
                                else:
                                    iTempData = str(iDevData[iData].encode('ascii', 'ignore'))

                            except:
                                if iData != 0:
                                    iTempData = iTempData+','+str(iDevData[iData]).encode('ascii', 'ignore')
                                else:
                                    iTempData = iDevData[iData].encode('ascii', 'ignore')

                    # Store the result
                    iInformation.append(iTempData)

            if len(iTablets)>0:
                for iTabletDevices in range(len(iTablets)):
                    iTempData = ''
                    iDevData = eval(iTablets[iTabletDevices])

                    if iDebug3:
                        indigo.server.log(u'Conversion field details for iTablet:'+str(iTabletDevices))
                        indigo.server.log(u'Battery:'+str(iDevData[3]))
                        indigo.server.log(u'TimeStamp:'+str(iDevData[10]))

                    for iData in range(len(iDevData)):
                        if iData == 3: # Battery Level
                            iTempData = iTempData+','+str(iDevData[3]*100)+'%'

                        elif iData == 10: # Time Stamp in ms
                            if type(iDevData[10]) == long:
                                iTime = time.asctime(time.localtime(int(iDevData[10]/1000.0)))
                                iTempData = iTempData+','+iTime
                            else:
                                if iDebug2:
                                    indigo.server.log(u'Warning - Time Stamp is absent for iTablet:'+str(iTabletDevices)
                                                      +u' iPhone is probably inactive')

                                iTempData = iTempData+','+"** No Timestamp **"
                                iTempData = iTempData+','+"None"
                                iTempData = iTempData+','+"0.0"
                                iTempData = iTempData+','+"0"
                                iTempData = iTempData+','+"0"
                                iTempData = iTempData+','+"True"
                                iTempData = iTempData+','+"True"
                        else:
                            try:
                                if iData != 0:
                                    iTempData = iTempData+','+str(iDevData[iData].encode('ascii', 'ignore'))
                                else:
                                    iTempData = str(iDevData[iData].encode('ascii', 'ignore'))
                            except:
                                if iData != 0:
                                    iTempData = iTempData+','+str(iDevData[iData]).encode('ascii', 'ignore')
                                else:
                                    iTempData = iDevData[iData].encode('ascii', 'ignore')

                    # Store the result
                    iInformation.append(iTempData)
        except:
            errorHandler('iAccount')
            if iDebug1:
                indigo.server.log(u'Critical - Failed to convert data from API - raise to Developer')

            return False, {}

        try:
            if iDebug3:
                indigo.server.log(u'Converting data before return...')

            # Convert to a list
            iDeviceInformation = []
            for deviceNumber in range(len(iInformation)):
                iDeviceInformation.append(iInformation[deviceNumber].split(','))

            iDeviceDict = {}
            iDeviceData = {}
            iCustStates = iCustomAPI()

            iDeviceInformation = []
            for deviceNumber in range(len(iInformation)):
                iDeviceInformation.append(iInformation[deviceNumber].split(','))

            for iItem in range(len(iDeviceInformation)):
                for iField in range(len(iCustStates)):
                    iDeviceData[iCustStates[iField]] = iDeviceInformation[iItem][iField]

                iDeviceDict['Phablet Device '+str(iItem+1)] = iDeviceData
                iDeviceData = {}

            if iDebug3:
                indigo.server.log(u'Data converted successfully...')

            return True, iDeviceDict

        except:
            errorHandler('iAccount')
            if iDebug1:
                indigo.server.log(u'Data conversion to list iDeviceDict failed...')
                return False, {}
    except:
        errorHandler('iAccount - General Failure')
        if iDebug1:
            indigo.server.log(u'Mapping failure - see error log for details...')
            return False, {}

    return True, iDeviceDict

def reverseLookup(iLat, iLong):

    ################################################
    # Uses pyGeocoder to reverse look up a device
    # Look up the latitude and longitude.  Limited to
    # 25,000 uses per pay.  User API means that they
    # get the full quota.

    try:
        result = Geocoder.reverse_geocode(float(iLat), float(iLong))
        iAddress = result.formatted_address
        iAddress = iAddress.split(',')
        iWaste = iAddress.pop(len(iAddress)-1)
        iReverse = ''
        iNumber = 0
        for item in range(len(iAddress)):
            if iNumber == 0:
                iReverse = iAddress[item]
                iNumber = iNumber + 1
            else:
                iReverse = iReverse+','+iAddress[item]
    except:
        errorHandler('reverseLookup')
        # Too many queries in one day... stop looking
        iReverse = '** Too many queries in one day **'
        pass

    return iReverse


def updateDevice(dev, iDeviceDict, iStates, iKey):

    ################################################
    # Updates all states of a device on the indigo server

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, iDebug5, gUnits, fingScanLink

    try:
        if False:
            indigo.server.log(u'Attempting to update:'+dev.name)

        # Set up change in indicator flags
        iIndicator1 = False
        iIndicator2 = False

        if dev.states['deviceActive'] == 'true':
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
        else:
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            iIndicator1 = True

        for iField in iStates:
            if iField == 'deviceAccuracy':
                # This is always in metres so may need to convert if imperial - use the standard conversion module
                iAccurate = convertUnits(float(iDeviceDict[iKey][iField]))
                dev.updateStateOnServer(iField, value = str(round(iAccurate[1],2)))

            elif iField=='deviceInaccurate' or iField=='deviceIsOldPosition' or iField=='deviceLocationEnabled':
                if iDeviceDict[iKey][iField] == "true" and not iIndicator2:
                    iIndicator2 = True
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

            elif iField=='deviceBattery':
                # Update a new state called deviceBatteryLevel
                if len(iDeviceDict[iKey][iField]) != 0:
                    iBatteryVal = int(iDeviceDict[iKey][iField][:-1])
                    dev.updateStateOnServer('deviceBatteryLevel', value = iBatteryVal)
                    dev.updateStateOnServer('deviceBattery', value = str(iBatteryVal)+'%')

            elif iField=='deviceIsMac':
                # Update a new state called deviceBatteryLevel
                if len(iDeviceDict[iKey][iField])>0 and iDeviceDict[iKey][iField] == 'True':
                    iBatteryVal = 100
                    dev.updateStateOnServer('deviceBatteryLevel', value = iBatteryVal)
                    dev.updateStateOnServer('deviceBattery', value = str(iBatteryVal)+'%')
                    dev.updateStateOnServer('batteryOnCharge', value = 'On Mains Power')

            else:
                dev.updateStateOnServer(iField, value = iDeviceDict[iKey][iField])

            if iField == 'deviceLatitude' or iField == 'deviceLongitude':
                if iDebug1 or iDebug2:
                    indigo.server.log('Device update (l/l):'+dev.name+' '+str(iDeviceDict[iKey][iField]))

        # Store the address if necessary
        # Have we actually moved much?
        iLat = float(dev.states['deviceLatitude'])
        iLong = float(dev.states['deviceLongitude'])
        uLat = float(dev.states['ULat'])
        uLong = float(dev.states['ULong'])

        if uLat == 0.0 and uLong == 0.0:
            # First update so copy the device latutudes
            dev.updateStateOnServer('ULat', value = iLat)
            dev.updateStateOnServer('ULong', value = iLong)
            iAddress = reverseLookup(dev.states['deviceLatitude'], dev.states['deviceLongitude'])
            dev.updateStateOnServer('deviceAddress',iAddress)
            dev.updateStateOnServer('UMoved', value = True)
            dev.updateStateOnServer('loggedTrack', value = 'false')

        else:
            uDistCalc = iDistance(iLat, iLong, uLat, uLong)

            # Convert to the current units
            uDistance = convertUnits(uDistCalc[1])

            devProps = dev.pluginProps
            if 'UDist' in devProps:
                uTrigger = float(devProps['UDist'])
            else:
                uTrigger = 100.0

            if uDistance[1] > uTrigger:
                # We've moved beyond our update trigger so update address
                # and add another entry into the tracking database if required
                iAddress = reverseLookup(dev.states['deviceLatitude'], dev.states['deviceLongitude'])
                dev.updateStateOnServer('deviceAddress',iAddress)

                # Now remember the new position
                dev.updateStateOnServer('ULat', value = iLat)
                dev.updateStateOnServer('ULong', value = iLong)
                dev.updateStateOnServer('UMoved', value = True)
                dev.updateStateOnServer('loggedTrack', value = 'false')
            else:
                dev.updateStateOnServer('UMoved', value = False)
                dev.updateStateOnServer('loggedTrack', value = 'true')

        if dev.states['deviceActive'] == 'false':
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

        #############  added Karl Wachs trigger update of fingscan module
        if fingScanLink:
            fingscanPlug=indigo.server.getPlugin("com.karlwachs.fingscan")
            try:
                if fingscanPlug.isEnabled():
                    fingscanPlug.executeAction("actionFrom", props ={"from":"com.corporatechameleon.iFindplugBeta", "msg":unicode(dev.id)})  ## this format will tell who is calling and which device has changed
                else:
                    if iDebug3:
                     indigo.server.log("Trigger fingscan not enabled")
            except:
                errorHandler('FINGScan Access')
                if iDebug3:
                    indigo.server.log("Rrror calling fingscan plugin update")

        #############  end

        return True, "OK"

    except:
        errorHandler('updateDevice - GF4')
        if iDebug2:
           indigo.server.log(u'Problems updating states & images for device:'+dev.name)

        return False, 'GF4'

    return True, 'OK'

def timeValidate(myTime="00:00-00:00"):
    # Check format is correct
    if len(myTime.strip()) == 0:
        # Field is blank so just return
        return True, "Blank Range - ignored"

    if myTime[2] != ':' or myTime[-3] != ":":
        # Error in format
        if iDebug2:
            indigo.server.log("Format for this field must be HH:MM - HH:MM")

        return False, "Missing ':' in time"

    else:
        myStartHrs = myTime[0:2]
        myStartMins = myTime[3:5]
        myEndHrs = myTime[-5:-3]
        myEndMins = myTime[-2:]
        try:
            startHrs = int(myStartHrs)
            startMins = int(myStartMins)
            endHrs = int(myEndHrs)
            myEndMins = int(myEndMins)

        except ValueError:
            errorHandler('timeValidate')
            # non-numeric in time range
            if iDebug2:
                    indigo.server.log("Time range contains a non-numeric character - "
                                      "format must be HH:MM-HH:MM where H & M must be numeric")

            return False, "Non-numeric in HH or MM field"

    return True, "Ok"

def rangeCheck(myTime = "00:00-00:00"):
    ############################################
    # Checks if the time now is in a specific time range
    # For a feature on a device

    # Check format is correct
    checkTimeFormat = timeValidate(myTime)

    if checkTimeFormat[0]:
        if myTime.replace(" ","")=="00:00-00:00":
            return True, "Default range specified"

        if checkTimeFormat[1].find('Blank') == -1:
            myStartHrs = myTime[0:2]
            myStartMins = myTime[3:5]
            myEndHrs = myTime[-5:-3]
            myEndMins = myTime[-2:]
            timeNow = datetime.datetime.now()
            timeRangeStart = datetime.datetime(timeNow.year, timeNow.month, timeNow.day, int(myStartHrs), int(myStartMins), 0)
            timeRangeEnd = datetime.datetime(timeNow.year, timeNow.month, timeNow.day, int(myEndHrs), int(myEndMins), 0)
            if timeRangeEnd < timeRangeStart:
                # Ends before it Starts so must be the following day!
                if iDebug2:
                    indigo.server.log('Adjusting end date to following day...')

                timeInc = datetime.timedelta(1)
                timeRangeEnd = timeRangeEnd+timeInc

            if timeNow >= timeRangeStart and timeNow <= timeRangeEnd:
                return True, "In range"
            else:
                return False, "Out of range"
        else:
            # Time range is blank so return True
            return True, "Blank"
    else:
        return False, "Format error"

def nextUpdateCalc(dev):

    ################################################
    # Calculates the time of the next update based on the options set by the user
    # Options are Battery Level, HolidayMode, NightMode, StationaryMode and GeoFence Power Saving Mode
    # Stationary is non-operational in this release

    global gUnits
    iDevProps = dev.pluginProps
    try:
        iFutureTime = int(iDevProps['frequencyTimer'])
        iBatteryTime = int(iDevProps['frequencyTimer'])
    except:
        errorHandler('nextUpdateCalc')
        iFutureTime = 600
        iBatteryTime = 600

    iDistanceTime = 0
    iHomeTime = 0
    iPowerTime = 0
    iNightTime = 0
    iStationaryTime = 0
    iScheduleTime1 = 0
    iScheduleTime2 = 0
    iScheduleTime3 = 0

    iTimes = []

    if iDebug3:
        indigo.server.log(u'Recalculating update time...')

    # Battery level or charging mode check
    try:
        if dev.states['deviceBatteryLevel'] == 0:
            # Don't change anything - no probably no update
            # From the most recent API from Apple
            pass

        elif dev.states['batteryOnCharge'] == 'Charging' or dev.states['batteryOnCharge'] == 'Charged':
            # Battery is connected to power or is >80% so we can revert to the 50% + level
            iBatteryTime = int(iDevProps['frequencyTimer'])
            return iBatteryTime

        elif dev.states['deviceBatteryLevel'] > 50:
            iBatteryTime = int(iDevProps['frequencyTimer'])
        elif dev.states['deviceBatteryLevel']<51 and dev.states['deviceBatteryLevel']>40:
            iBatteryTime = int(iDevProps['frequency50'])
        elif dev.states['deviceBatteryLevel']<41 and dev.states['deviceBatteryLevel']>30:
            iBatteryTime = int(iDevProps['frequency40'])
        else:
            iBatteryTime = int(iDevProps['frequency30'])
    except:
        errorHandler('nextUpdateCalc - Battery')

    # Now check Holiday Mode
    try:
        if 'holidayMode' in iDevProps:
            if iDevProps['holidayMode']:
                # Holiday Mode is set in metres or feet
                holDistance = float(iDevProps['distanceHoliday'])
                homDistance = convertUnits(float(dev.states['distanceHome']))

                if homDistance[1]>holDistance:
                    if 'holidayFrequency' in iDevProps:
                        iDistanceTime = int(iDevProps['holidayFrequency'])
                    else:
                        iDistanceTime = 0
        else:
            iDevProps['holidayMode'] = False
            iDevProps['holidayFrequency'] = 0
            dev.replacePluginPropsOnServer(iDevProps)
            iDistanceTime = 0
    except:
        errorHandler('nextUpdateCalc - Holiday')

    # Check Night Mode
    try:
        if iDevProps['nightMode']:

            # Is there a range specified?
            if 'nightTime' in iDevProps:
                if len(iDevProps['nightTime']) == 0 or iDevProps['nightTime'].replace(" ","") == "00:00-00:00":
                    # It's blank or set to default
                    dayTime = indigo.variables["isDaylight"].value
                    if not dayTime:
                        if 'nightFrequency' in iDevProps:
                            if iDevProps['nightFrequency'] != 0:
                                iNightTime = int(iDevProps['nightFrequency'])
                            else:
                                iNightTime = 1800 # 30 mins default
                        else:
                            iNightTime = 1800 # 30 mins default

                elif len(iDevProps['nightTime']) != 0 or iDevProps['nightTime'].replace(" ","") != "00:00-00:00":
                    # Are we in the range specified for night?
                    checkRange = rangeCheck(iDevProps['nightTime'].replace(" ",""))
                    if checkRange[0]:
                        # In range
                        if 'nightFrequency' in iDevProps:
                            if iDevProps['nightFrequency'] != 0:
                                iNightTime = int(iDevProps['nightFrequency'])
                            else:
                                iNightTime = 1800 # 30 mins default
                        else:
                            iNightTime = 1800 # 30 mins default
                    else:
                        # Not in range so set to 0
                         iNightTime = 0
    except:
        errorHandler('nextUpdateCalc - Night Mode')

    # Check if in a Power Saving Geo
    try:
        if iDevProps['powerSaveMode']:
            # Check current GeoFence
            iRange = dev.states['deviceInGeoRange']
            iGeoName = dev.states['deviceNearestGeoName']
            iGeoMatch = False
            iPowerSave = False
            iPowerTimeRange = "00:00-00:00"
            iPowerFrequency = "0"

            if iRange == 'true':
                # In range of a Geo - check if it's power saving
                for geo in indigo.devices.iter('self.iGeoFence'):
                    geoProps= geo.pluginProps

                    if not iGeoName == geoProps['geoName']:
                        continue
                    else:
                        iPowerSave = geoProps['geoPower']

                        if 'powerTime' in iDevProps:
                            iPowerTimeRange = iDevProps['powerTime']
                        else:
                            iPowerTimeRange = "00:00-00:00"
                        if 'powerFrequency' in iDevProps:
                            if iDevProps['powerFrequency'] >0:
                                iPowerFrequency = int(iDevProps['powerFrequency'])
                            else:
                                iPowerFrequency = 0
                        else:
                            # No frequency specfied so assume default
                            iPowerFrequency = 1800 # 30 mins default
                        break


                if iPowerSave and (len(iPowerTimeRange) != 0 or iPowerTimeRange.replace(" ","") != "00:00-00:00"):
                    # Are we in the range specified for GeoSavings?
                    checkRange = rangeCheck(iPowerTimeRange.replace(" ",""))

                    if checkRange[0]:
                        # In range
                            if int(iPowerFrequency) > 0:
                                iPowerTime = int(iPowerFrequency)
                            else:
                                iPowerTime = 900 # 15 mins default
                    else:
                        # Not in time range so set to 0
                        iPowerTime = 0

                elif iPowerSave and (len(iPowerTimeRange) == 0 or iPowerTimeRange.replace(" ","") == "00:00-00:00"):
                    # It's blank or set to default
                    if int(iPowerFrequency) > 0:
                        iPowerTime = int(iPowerFrequency)
                    else:
                        iPowerTime = 900 # 15 mins default
    except:
        errorHandler('nextUpdateCalc - Power Mode')

    # Check if in Home mode
    try:
        if iDevProps['homeMode']:
            # If at home then delay to ten mins if at Home
            # We must be in the Home GeoFence
            iHomeSave = False
            if dev.states['deviceInGeoRange'] == 'true':
                iGeoName = dev.states['deviceNearestGeoName']
                iHomeSave = False

                # In a range but is it the Home range?
                for geo in indigo.devices.iter('self.iGeoFence'):
                    geoProps= geo.pluginProps
                    if not iGeoName.strip() == geoProps['geoName'].strip():
                        continue
                    else:
                        iHomeSave = geoProps['geoHome']
                        break

            if iHomeSave:
                # We're in the home geo so now look at what to do
                if 'homeTime' in iDevProps:
                    if len(iDevProps['homeTime']) != 0 or iDevProps['homeTime'].replace(" ","") != "00:00-00:00":
                        # Are we in the range specified for night?
                        checkRange = rangeCheck(iDevProps['homeTime'].replace(" ",""))
                        if checkRange[0]:
                            # In range
                            if 'homeFrequency' in iDevProps:
                                if iDevProps['homeFrequency'] != 0:
                                    iHomeTime = iDevProps['homeFrequency']
                                else:
                                    iHomeTime = 1800 # 30 mins default
                            else:
                                iHomeTime = 1800 # 30 mins default
                        else:
                            # Not in range so set to 0
                            iHomeTime = 0

                    elif len(iDevProps['homeTime']) == 0 or iDevProps['homeTime'].replace(" ","") == "00:00-00:00":
                        # It's blank or set to default
                        if int(iDevProps['homeFrequency']) > 0:
                            iHomeTime = int(iDevProps['homeFrequency'])
                        else:
                            iHomeTime = 900 # 15 mins default
                else:
                    iHomeTime = 900 # 15 min default
    except:
        errorHandler('nextUpdateCalc - Home Mode')

    # Check if in schedule mode
    try:

        if 'scheduleMode' in iDevProps:
            if iDevProps['scheduleMode']:
                # Wants to schedule downtimes
                # This is independant of the geofence

                # Check schedule 1
                if 'scheduleTime1' in iDevProps:
                    if len(iDevProps['scheduleTime1']) != 0 and iDevProps['scheduleTime1'].replace(" ","") !="00:00-00:00":
                        # There is a time set in schedule 1 so check it out.
                        # Are we in that range specified schedule 1?
                        checkRange = rangeCheck(iDevProps['scheduleTime1'].replace(" ",""))
                        if checkRange[0]:
                            # In range
                            if 'scheduleFrequency' in iDevProps:
                                if iDevProps['scheduleFrequency'] != 0:
                                    iScheduleTime1 = int(iDevProps['scheduleFrequency'])
                                else:
                                    iScheduleTime1 = 1800 # 30 mins default
                            else:
                                iScheduleTime1 = 1800 # 30 mins default
                        else:
                            # Not in range so set to 0
                            iScheduleTime1 = 0
                    else:
                        iScheduleTime1 = 0
                else:
                    iScheduleTime1 = 0

                # Check schedule 2
                if 'scheduleTime2' in iDevProps:
                    if len(iDevProps['scheduleTime2']) != 0 and iDevProps['scheduleTime2'].replace(" ","") !="00:00-00:00":
                        # There is a time set in schedule 1 so check it out.
                        # Are we in that range specified schedule 1?
                        checkRange = rangeCheck(iDevProps['scheduleTime2'].replace(" ",""))
                        if checkRange[0]:
                            # In range
                            if 'scheduleFrequency' in iDevProps:
                                if iDevProps['scheduleFrequency'] != 0:
                                    iScheduleTime2 = int(iDevProps['scheduleFrequency'])
                                else:
                                    iScheduleTime2 = 1800 # 30 mins default
                            else:
                                iScheduleTime2 = 1800 # 30 mins default
                        else:
                            # Not in range so set to 0
                            iScheduleTime2 = 0
                    else:
                        iScheduleTime2 = 0
                else:
                    iScheduleTime2 = 0

                # Check schedule 3
                if 'scheduleTime3' in iDevProps:
                    if len(iDevProps['scheduleTime3']) != 0 and iDevProps['scheduleTime3'].replace(" ","") !="00:00-00:00":
                        # There is a time set in schedule 3 so check it out.
                        # Are we in that range specified schedule 3?
                        checkRange = rangeCheck(iDevProps['scheduleTime3'].replace(" ",""))
                        if checkRange[0]:
                            # In range
                            if 'scheduleFrequency' in iDevProps:
                                if iDevProps['scheduleFrequency'] != 0:
                                    iScheduleTime3 = int(iDevProps['scheduleFrequency'])
                                else:
                                    iScheduleTime3 = 1800 # 30 mins default
                            else:
                                iScheduleTime3 = 1800 # 30 mins default
                        else:
                            # Not in range so set to 0
                            iScheduleTime3 = 0
                    else:
                        iScheduleTime3 = 0
                else:
                    iScheduleTime3 = 0
    except:
        errorHandler('nextUpdateCalc - Schedule Mode')

    # Check if in Stationary mode
    try:
        if iDevProps['stationaryMode']:
            # Check if stationary using speed calculation
            # Calculate the distance travelled
            if dev.states['oldLat'] == 0 or dev.states['oldLong'] == 0:

                # Never been updated so update and forget
                iLat = dev.states['deviceLatitude']
                iLong = dev.states['deviceLongitude']
                dev.updateStateOnServer('oldLat', value=iLat)
                dev.updateStateOnServer('oldLong', value=iLong)
                dev.updateStateOnServer('lastStationaryCheck', value = int(time.time()))
                dev.updateStateOnServer('deviceStationary', value = 0)
                iStationaryTime = 0

            else:
                # Calculate the distance between the new and old positions
                iOldLat = float(dev.states['oldLat'])
                iOldLong = float(dev.states['oldLong'])
                iNewLat = float(dev.states['deviceLatitude'])
                iNewLong = float(dev.states['deviceLongitude'])
                iDistanceTravelled= iDistance(iOldLat, iOldLong, iNewLat,iNewLong)

                # Use Correct Units
                iDistanceTravelled = convertUnits(iDistanceTravelled[1])

                iDeviceStationary = int(dev.states['deviceStationary'])
                iDevStationaryTime = int(dev.states['lastStationaryCheck'])

                if iDevStationaryTime == 0:
                    # Never been checked so remember now and then forget it
                    iStationaryTime = 0
                    dev.updateStateOnServer('lastStationaryCheck', value = int(time.time()))
                    dev.updateStateOnServer('oldLat', value=iNewLat)
                    dev.updateStateOnServer('oldLong', value = iNewLong)
                    dev.updateStateOnServer('deviceStationary', value = 0)

                else:
                    # Need to calculate the speed based on distance/time
                    # Time passed
                    iNow = int(time.time())
                    iTimeDiff = iNow - iDevStationaryTime
                    if 'distanceTime' in iDevProps:
                        iTimeTrigger = int(iDevProps['distanceTime'])
                    else:
                        iTimeTrigger = 600

                    if 'distanceFrequency' in iDevProps:
                        iTimeFrequency = int(iDevProps['distanceFrequency'])
                    else:
                        iTimeFrequency = 600

                    if iTimeDiff <= iTimeTrigger:
                        # Not stationary for long enough yet so don't bother
                        dev.updateStateOnServer('deviceStationary', value = dev.states['deviceStationary']+iTimeDiff)

                    else:
                        # Passed the trigger for a stationary check
                        if iTimeDiff > 0:
                            iDevProps = dev.pluginProps
                            try:
                                iSpeed = float(iDistanceTravelled[1]/iTimeDiff)

                            except ZeroDivisionError:
                                iSpeed = 1.0

                            # Use device speed trigger in mph or kmh
                            iDevSpeed = float(iDevProps['speedStation'])

                            # Use Correct Units for user selection
                            if gUnits == 'Metres' or gUnits == 'Metric':
                                iDevSpeed = iDevSpeed * 0.277778 # Convert km/h to m/s
                            else:
                                iDevSpeed = iDevSpeed * 0.44704 # Convert mph to m/s

                            if iSpeed<=iDevSpeed:
                                # It's stationary so change the update frequency
                                iStationaryTime = int(iDevProps['distanceFrequency'])
                                dev.updateStateOnServer('deviceStationary', value=iDeviceStationary+iTimeDiff)

                            else:
                                # It's moving over the last period
                                dev.updateStateOnServer('deviceStationary', value = 0)
                                iStationaryTime = 0

                            dev.updateStateOnServer('lastStationaryCheck', value = int(time.time()))
                            dev.updateStateOnServer('oldLat', value=iNewLat)
                            dev.updateStateOnServer('oldLong', value = iNewLong)

        else:
            iStationaryTime = 0
    except:
        errorHandler('nextUpdateCalc - Stationary Mode')

    # Check for the biggest
    try:
        iTimes.append(iPowerTime)
        iTimes.append(iDistanceTime)
        iTimes.append(iNightTime)
        iTimes.append(iStationaryTime)
        iTimes.append(iBatteryTime)
        iTimes.append(iHomeTime)
        iTimes.append(iScheduleTime1)
        iTimes.append(iScheduleTime2)
        iTimes.append(iScheduleTime3)

        if iDebug2:
            indigo.server.log(dev.name+' Power, Distance, Night, Stationary, Battery, Home, Holiday,Schedule1, Schedule2, Schedule3')
            indigo.server.log('Values: '+str(iPowerTime)+' '+str(iDistanceTime)+' '+str(iNightTime)+' '+str(iStationaryTime)+' '
                              +str(iBatteryTime)+' '+str(iHomeTime)+' '+str(iScheduleTime1)+' '+str(iScheduleTime2)+' '
                              +str(iScheduleTime3))

        # Find biggest
        iTimes.sort()

        # Added time in s
        iFutureTime = iTimes[-1]

        # Save as a state
        dev.updateStateOnServer('secondsNextUpdate', value=iFutureTime)

        return iFutureTime
    except:
        errorHandler('nextUpdateCalc - Time Calculation')
        return 600

def distanceCalculation(origin, final, APIKey, mode='driving',units="metric"):

    ################################################
    # Uses Google Maps Distance Matrix API to calculate travel distance and time.
    # Note that output is in km or m that must be converted to current units.
    # Limited to 2.500 uses/day and plugin restricts to 10 min frequency/device

    try:
        gmaps = googlemaps.Client(APIKey)
    except:
        errorHandler('distanceCalculation')
        indigo.server.log('Problem with Google Maps key - is it registered for Distance Matrix API?', isError=True)
        indigo.server.log('Check forum for details on how to authorise your key', isError=True)
        return 'FailAPI',""

    try:
        now = datetime.datetime.now()
        distance_result = gmaps.distance_matrix(origin,final,
                                                mode='driving', language=None, avoid=None, units='metric', departure_time=now,
                                                arrival_time=None, transit_mode=None, transit_routing_preference=None)

        iTimeTaken = distance_result['rows'][0]['elements'][0]['duration']['text']
        iDistCalc = distance_result['rows'][0]['elements'][0]['distance']['text']

        return iTimeTaken, iDistCalc

    except:
        errorHandler('distanceCalculation')

def miles_to_MilesFeet(milesDec, decimalPlaces=2, justMiles=False):

    ################################################
    # Convert miles to miles and feet
    # If less that 0.1 miles give only feet
    try:
        feetInMiles = 5280.0
        miles = int(milesDec)
        if justMiles:
            # Just send back truncated miles
            return str(round(milesDec,2))+' ml'

        if miles == 0:
            # Check if less than 0.1 otherwise return truncated value
            if milesDec>=0.05:
                # Just return truncated value
                return str(round(milesDec, decimalPlaces))+' ml'
            else:
                # Just return feet
                return str(round(milesDec*feetInMiles, decimalPlaces))+' ft'

        totalFeet = milesDec*feetInMiles
        remainingFeet = int(totalFeet - (float(miles)*feetInMiles))

        # Return the distance
        ftUnits=' ft'
        mlUnits=' ml'

        return str(miles)+mlUnits+' and '+str(remainingFeet)+ftUnits
    except:
        errorHandler('milesTo_MlFeet')

def kilometres_to_KmMetres(kiloDec, decimalPlaces=2, justKm = False):

    ################################################
    # Convert decimal kilometres to kilometers and metres
    # If less that 0.2 kilometres give only metres
    try:
        metresInKm = 1000
        kilometres = int(kiloDec)

        if justKm:
            # Just send back truncated km
            return str(round(kiloDec,2))+' km'

        if kilometres == 0:
        # Check if less than 0.1 otherwise return truncated value

            if kiloDec>=0.20:
                # Just return truncated value
                return str(round(kiloDec, decimalPlaces))+' km'
            else:
                # Just return feet
                return str(round(kiloDec*metresInKm, decimalPlaces))+' m'

        totalMetres = kiloDec*metresInKm
        remainingMetres = int(totalMetres - (float(kilometres)*metresInKm))

        # Return the distance
        mtUnits = ' m'
        kmUnits = ' km'

        return str(kilometres)+kmUnits+' and '+str(remainingMetres)+mtUnits

    except:
        errorHandler('milesTo_MlFeet')

def displayUnits():
    global gUnits
    try:
        if gUnits == 'Imperial':
            majorUnit = 'ml'
            minorUnit = 'ft'
        elif gUnits == 'Metric':
            majorUnit = 'km'
            minorUnit = 'm'
        else:
            majorUnit = 'm'
            minorUnit = 'm'

        return majorUnit, minorUnit

    except:
        errorHandler('displayUnits')

def convertUnits(iDist):
    ################################################
    # Converts the iDist to the current units
    # Returns two values per unit
    #   Metres - metres, metres
    #   Metric - kilometres, metres
    #   Imperial - miles and feet
    # Distances are always presented in metres to this module

    global gUnits
    try:
        # Conversion factors metres to....Source Google
        if gUnits == "Metres":
            iConversionFactor1 = 1
            iConversionFactor2 = 1
        elif gUnits == "Metric":
            iConversionFactor1 = 0.001
            iConversionFactor2 = 1
        else:
            iConversionFactor1 = 0.000621371
            iConversionFactor2 = 3.28084

        return iDist*iConversionFactor1, iDist*iConversionFactor2

    except:
        errorHandler('convertUnits')

def iDistance(lat1, long1, lat2, long2):

    ################################################
    # Calculates the 'As the crow flies' distance between
    # two points and returns value in metres

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, gUnits

    # First check if numbers are valid
    if lat1+long1 == 0.0 or lat2+long2 == 0.0:

        if iDebug2:
        #  Zero default sent through
            indigo.server.log(u'No distance calculation possible as values are 0,0,0,0')
        return False, 0.0

    # Convert latitude and longitude to
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0

    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians

    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians

    # Compute spherical distance from spherical coordinates.

    # For two locations in spherical coordinates
    # (1, theta, phi) and (1, theta', phi')
    # cosine( arc length ) =
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length

    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) +
           math.cos(phi1)*math.cos(phi2))
    try:
        arc = math.acos( cos )
    except:
        errorHandler('iDistance')
        arc = 1
        pass

    # Remember to multiply arc by the radius of the earth
    # e.g. m to get actual distance in m

    mt_radius_of_earth = 6373000.0

    distance = arc * mt_radius_of_earth

    return True, distance

def findHome():

    ################################################
    # Locates the Home Geo for Home Calculations including distance to
    # home and bearing to home.  Traps more than one home and returns an error
    # We need to ensure that the error is trapped and correctly properly
    # and that a user if fully aware that there are more than one GeoFence or none
    # and what they might be



    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, errorFile

    try:
        # Checks which GeoFence is designated as Home
        iNumberHome = 0
        iHomeId = 0
        iHomeGeoNameId = 0
        iSuccess = False
        iHomeName = 'No Home GeoFence Found'
        if iDebug5:
            indigo.server.log('\n** Starting Home GeoFence Search **')

        for dev in indigo.devices.iter('self.iGeoFence'):
            localProps = dev.pluginProps
            if not localProps['geoActive']:
                # This GeoFence is marked as inactive so ignore it
                continue

            if dev.name == 'Home Geofence' and iNumberHome == 0:
                if iDebug5:
                    indigo.server.log('--> Found a GeoFence called Home GeoFence')
                    indigo.server.log('--> ID:'+str(dev.id)+' Name:'+str(dev.name))
                    indigo.server.log('--> Active Status:'+str(localProps['geoActive']))

                iHomeGeoNameId = dev.id
                iHomeName = dev.name

            if 'geoHome' in localProps:
                    if localProps['geoHome'] == True:
                        if iDebug5:
                            indigo.server.log('--> Found a designated GeoFence.  Found:'+str(iNumberHome+1)+' so far')
                            indigo.server.log('--> ID:'+str(dev.id)+' Name:'+str(dev.name))
                            indigo.server.log('--> Active Status:'+str(localProps['geoActive']))

                        iHomeId = dev.id
                        iNumberHome = iNumberHome + 1
                        iHomeName = dev.name
        if iDebug5:
            indigo.server.log('--> Final Analysis:')
            indigo.server.log('Number of Designated Home GeoFences Found:'+str(iNumberHome))
            indigo.server.log('Named Home GeoFences Found:'+str(iHomeGeoNameId))


        if iNumberHome == 0 and iHomeGeoNameId == 0:
            # No Home listed
            indigo.server.log('--> FAILED - Found no Home GeoFences')
            if iDebug1:
                indigo.server.log(u'** No Home Geofence found please create or edit a current Geo **')

            iSuccess = False

        elif iNumberHome == 0 and not iHomeGeoNameId == 0:
            # Home GeoFence created but not designated
            if iDebug5:
                indigo.server.log('--> SUCCESS: Only found named Home GeoFence')
            try:
                newHome = indigo.devices[iHomeGeoNameId]
                localProps = newHome.pluginProps
                localProps['geoHome'] = True
                newHome.replacePluginPropsOnServer(localProps)
                iHomeId = iHomeGeoNameId
                if iDebug5:
                    indigo.server.log('--> SUCCESS: Named Home GeoFence updated to designated')
                iSuccess = True
                if iDebug2:
                    indigo.server.log(u'Home GeoFence not designated but assigned [Home GeoFence] device as Home')
            except:
                if iDebug5:
                    indigo.server.log('--> FAILED: Failed when updating Home GeoFence')

                errorHandler('findHome')
                if iDebug2:
                    indigo.server.log(u'Home GeoFence not designated but failed to assign [Home GeoFence] device as Home')
                iSuccess = False

        elif iNumberHome == 1:
            # Found Home GeoFence
            if iDebug5:
                    indigo.server.log('--> SUCCESS: Unique GeoFence Found:'+str(iHomeId)+' '+str(iHomeGeoNameId))

            iSuccess = True
            pass

        else:
            # More than one GeoFence
            iSuccess = False
            if iDebug5:
                    indigo.server.log('--> FAILED: Multiple Home GeoFences found:'+str(iNumberHome))

            if iDebug2:
                indigo.server.log(u'** There is more than one Home GeoFence Active - please check **')
    except:
        errorHandler('findHome')
        if iDebug1:
                indigo.server.log(u'Failed to complete search for Home GeoFence - raise with Developer')

    if iDebug5:
            indigo.server.log('--> RETURNED: Success:'+str(iSuccess)+' HomeId:'+str(iHomeId)+' Name:'+str(iHomeName))
            indigo.server.log('** End of Home Analysis **'+'\n')

    if not iSuccess:
        # There's an issue so report the details...
        indigo.server.log('Error in Home GeoFence setup - please review iFindStuffErrors.log for more information', isError=True)
        indigo.server.log('Have you recently deleted, inactivated or edited the Home GeoFence - if so check your setup?')
        indigo.server.log('Alternatively - have you created a unique Home GeoFence (e.g. checked Home Geo on only one GeoFence Device)?')
        indigo.server.log('You can also select Debug option 5 - Distance & Bearing Calculations to view error trace', isError = True)
        indigo.server.log('or contact the developer for support via the forum', isError = True)
        f = open(errorFile,'a')
        f.write('-'*80+'\n')
        f.write('Exception Logged:'+str(time.strftime(time.asctime()))+' in findHome module'+'\n\n')
        f.write('Values returned:'+str(iSuccess)+' HomeId:'+str(iHomeId)+' Name:'+str(iHomeName)+"\n")
        f.write('You have:'+str(iNumberHome)+' Home Geofences active\n')
        f.write('Please check that you have at least ONE and ONE only designated (e.g. Is Home Geo boxed checked in device configuration)\n')
        f.write('-'*80+'\n')
        f.close()


    return iSuccess, iHomeId, iHomeName

def iCardinal(d):

    ################################################
    # Converts bearing to compass point (as a string)

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

    try:
        # Converts degrees bearing to Cardinal
        majors   = 'north east south west'.split()
        majors   *= 2 # no need for modulo later
        quarter1 = 'N,N by E,N-NE,NE by N,NE,NE by E,E-NE,E by N'.split(',')
        quarter2 = [p.replace('NE','EN') for p in quarter1]
        d = (d % 360) + 360/64
        majorindex, minor = divmod(d, 90.)
        majorindex = int(majorindex)
        minorindex  = int( (minor*4) // 45 )
        p1, p2 = majors[majorindex: majorindex+2]
        if p1 in ['north','south']:
            q = quarter1
        else:
            q = quarter2

        if iDebug3:
            indigo.server.log('Direction of Home = '+q[minorindex].replace('N', p1).replace('E', p2).capitalize())

        return q[minorindex].replace('N', p1).replace('E', p2).capitalize()

    except:
        errorHandler('iCardinal')
        if iDebug1:
            indigo.server.log(u'Code failure in defining Cardinal Value for:'+str(d))
        return 'No compass bearing found!'

def iCompass(origin, destination):

    ################################################
    # Maps all of the devices contained in an account including Family devices
    # Routine calculates the angle from home and then also converts to a N.S.W.E tag\
    # Used to calculate the angle between the latitude and longitude of the origin & destination.
    # Thanks to kw123 for this contribution
    # Using:  http://www.ig.utexas.edu/outreach/googleearth/latlong.html
    # this one works right quadrants north = 0, east =90, s =180, w =270 degrees

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

    try:
        import math
        lat1, lon1 = origin
        lat2, lon2 = destination
        lat1= math.radians(lat1)
        lat2= math.radians(lat2)
        lon1= math.radians(lon1)
        lon2= math.radians(lon2)
        y = math.sin(lon2-lon1)*math.cos(lat2)
        x = math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(lon2-lon1)
        if y == 0.:
            if x >  0. : theta =  0.
            if x <  0. : theta =  180.
            if x == 0. : theta =  0.  # 2 points are the same
            return theta

        theta= math.degrees(math.atan2(y,x))%360.

        iHeading = iCardinal(theta)

        return theta, iHeading

    except:
        errorHandler('iCompass')
        if iDebug2:
            indigo.server.log(u'Code failure in calculating bearings - raise with Developer')

def iGeoLocation(iTracking='false',mapAPI='No Key', iDecimal=2, iUseRealDistance=False, iUseRealDistanceMode = "driving"):

    ################################################
    # Routine calculates all geolocation information for each device and geofence
    # including distances, range entry/exit, NEST actions, etc
    # and updates the states against each device/geofence

    global iDebug1, iDebug2, iDebug3,iDebug4, gUnits, db, iTrackHistory

    # Routine checks each module device and determines the nearest GeoLocation and if it's in range (in m)
    # and then updates the devices accordingly
    try:
        # Reference information
        iHome = findHome()
        iIssues = False
        iDecimal=int(iDecimal)

        for dev in indigo.devices.iter('self.iAppleDeviceAuto'):

            if not(dev.configured and dev.enabled):
                # This device isn't ready yet so ignore it!
                continue

            iRefDistance = 50000000.0
            iRefRealDistance = ""
            iRefRealTime = ""

            iDevName = dev.states['deviceName']

            # Ignore any inactive devices
            if dev.states['deviceActive'] == 'false' or dev.states['deviceLatitude'] == 0.0 or dev.states['deviceLongitude']==0.0:
                if iDebug2:
                    indigo.server.log(u'Device '+dev.name+u' is inactive or offline so ignored')

                # Update Inactive States states
                dev.updateStateOnServer('deviceLatitude', value='0.0')
                dev.updateStateOnServer('deviceLongitude',value='0.0')
                dev.updateStateOnServer('deviceNearestGeoName',value='Unknown')
                dev.updateStateOnServer('deviceInGeoRange', value= 'false')
                dev.updateStateOnServer('deviceGeoDistance', value='0')
                dev.updateStateOnServer('deviceInNestRange',value= 'false')
                dev.updateStateOnServer('distanceHome', value='0.0')
                dev.updateStateOnServer('geoDistanceDisplay', value='')
                dev.updateStateOnServer('geoHomeDistanceDisplay', value='')
                dev.updateStateOnServer('realDistanceHome', value='')
                dev.updateStateOnServer('realTimeHome', value='')
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                continue

            try:
                # Extract the location information
                if (dev.states['deviceLatitude'] != 0 and dev.states['deviceLongitude'] != 0):

                    iDevLatitude = float(dev.states['deviceLatitude'])
                    iDevLongitude = float(dev.states['deviceLongitude'])
                    iDevName = dev.states['deviceName']
                    iDevGeoName = dev.states['deviceNearestGeoName']
                    iDevGeoInRange = 'false'
                    iDevGeoDistance = dev.states['deviceGeoDistance']
                    iDevNestRange = 'false'
                    iIssues = True
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    if dev.states['deviceAddress'] == '** Unknown Phone Offline **':
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                    try:
                        # Look at each location in turn
                        for geoDevices in indigo.devices.iter('self.iGeoFence'):

                            # Get the geoLocation information from the device
                            localProps = geoDevices.pluginProps
                            if not 'geoName' in localProps:
                                continue

                            igeoName = localProps['geoName']
                            igeoLong = float(localProps['geoLongitude'])
                            igeoLat = float(localProps['geoLatitude'])
                            igeoActive = localProps['geoActive']
                            igeoNEST = localProps['geoNEST']
                            igeoRangeDistance = int(localProps['geoRange'])

                            if not igeoActive:
                                # This device isn't active so ignore it
                                if iDebug3:
                                    indigo.server.log('Geo Device:'+str(igeoName)+' ignored as inactive')
                                continue

                            if iDebug4:
                                indigo.server.log('Geo Details on check:'+str(igeoName)+' '+str(igeoActive))

                            # Now check the distance for each device
                            # Calculate the distance
                            if iDebug4:
                                indigo.server.log('Point 1'+' '+str(igeoLat)+','+str(igeoLong)+' Point 2 '+str(iDevLatitude)+','+str(iDevLongitude))

                            iSeparation = iDistance(igeoLat, igeoLong, iDevLatitude, iDevLongitude)

                            # Separation always returned in metres so we may need to convert

                            if not iSeparation[0]:
                                # Problem with the distance so ignore and move on
                                continue

                            iSeparationABS = abs(iSeparation[1])

                            # Return Correct Units
                            iDistSep = convertUnits(iSeparationABS)

                            #if iDebug5:
                            #    indigo.server.log('Converted the distance in metres:'+str(iSeparationABS)+" to "+gUnits+" "+str(iDistSep[0]))

                            # Set zero check
                            iGeoDistance0 = 0
                            iGeoDistance1 = 0

                            # Check against the reference
                            if iDistSep[0] <= iRefDistance:
                                iRefDistance = iDistSep[0]

                                # This is closer to this GeoLocation

                                iDevGeoName = igeoName
                                iGeoDistance0 = iDistSep[0]
                                iGeoDistance1 = iDistSep[1]

                                if iGeoDistance1 <= igeoRangeDistance:
                                    # In the range comparing distance in smaller units (m or ft) with igeoRangeDistance in ft or m

                                    iDevGeoInRange = 'true'
                                else:
                                    iDevGeoInRange = 'false'

                                if iDevGeoInRange == 'true' and igeoNEST:
                                    iDevNestRange = 'true'

                                else:
                                    iDevNestRange = 'false'

                    except:
                        errorHandler('iGeoLocation')
                        if iDebug2:
                            indigo.server.log(u'Problems when calculating distances and range information')
                            iIssues = True
                    try:
                        # Device nearest geo found
                        # Update the device and triggers

                        if iDevGeoName == dev.states['deviceNearestGeoName']:
                            # Device hasn't moved to another GeoRange
                                if iDevGeoInRange == dev.states['deviceInGeoRange']:
                                    # Still in the same place so ignore
                                    dev.updateStateOnServer('deviceEntered', value='false')
                                    dev.updateStateOnServer('deviceLeft', value='false')
                                    dev.updateStateOnServer('deviceInGeoRange', value=iDevGeoInRange)
                                    dev.updateStateOnServer('deviceInNestRange', value=iDevNestRange)
                                else:
                                    # Range flag has changed so is the new one true or false?
                                    if iDevGeoInRange == 'true':
                                        # Moved into the range this update
                                        dev.updateStateOnServer('deviceInGeoRange', value='true')
                                        dev.updateStateOnServer('deviceEntered', 'true')
                                        dev.updateStateOnServer('deviceLeft', 'false')
                                        dev.updateStateOnServer('deviceEnteredGeo', value=iDevGeoName)
                                        dev.updateStateOnServer('deviceLeftGeo', value='')
                                        dev.updateStateOnServer('deviceInNestRange', value=iDevNestRange)
                                        if iTracking:
                                            indigo.server.log(iDevName+' has entered GeoFence '+iDevGeoName)

                                    elif iDevGeoInRange == 'false':
                                        dev.updateStateOnServer('deviceInGeoRange', value='false')
                                        dev.updateStateOnServer('deviceEntered', value= 'false')
                                        dev.updateStateOnServer('deviceLeft', value = 'true')
                                        dev.updateStateOnServer('deviceLeftGeo', value=iDevGeoName)
                                        dev.updateStateOnServer('deviceEnteredGeo', value='')
                                        dev.updateStateOnServer('deviceInNestRange', value='false')
                                        if iTracking:
                                            indigo.server.log(iDevName+' has left GeoFence '+iDevGeoName)

                        else:
                            # Device has changed GeoRange
                            # Remember the Old Name for tracking
                            iOldGeoName = dev.states['deviceNearestGeoName']
                            dev.updateStateOnServer('deviceNearestGeoName', value = iDevGeoName)

                            if iDevGeoInRange == dev.states['deviceInGeoRange']:
                                if iDevGeoInRange == 'true':
                                    # Moved into the range this update
                                    dev.updateStateOnServer('deviceInGeoRange', value='true')
                                    dev.updateStateOnServer('deviceEntered', 'true')
                                    dev.updateStateOnServer('deviceLeft', 'true')
                                    dev.updateStateOnServer('deviceLeftGeo', value=iOldGeoName)
                                    dev.updateStateOnServer('deviceEnteredGeo', value=iDevGeoName)
                                    dev.updateStateOnServer('deviceInNestRange', value=iDevNestRange)
                                    if iTracking:
                                        indigo.server.log(iDevName+' has left GeoFence '+iOldGeoName)
                                        indigo.server.log(iDevName+' has entered GeoFence '+iDevGeoName)

                                elif iDevGeoInRange == 'false':
                                    dev.updateStateOnServer('deviceInGeoRange', value='false')
                                    dev.updateStateOnServer('deviceEntered', value= 'false')
                                    dev.updateStateOnServer('deviceLeft', value = 'false')
                                    dev.updateStateOnServer('deviceLeftGeo', value='')
                                    dev.updateStateOnServer('deviceEnteredGeo', value='')
                                    dev.updateStateOnServer('deviceInNestRange', value='false')

                            else:
                                # Range flag has changed so is the new one true or false?
                                if iDevGeoInRange == 'true':
                                    # Moved into the range this update
                                    dev.updateStateOnServer('deviceInGeoRange', value='true')
                                    dev.updateStateOnServer('deviceEntered', 'true')
                                    dev.updateStateOnServer('deviceLeft', 'false')
                                    dev.updateStateOnServer('deviceLeftGeo', value='')
                                    dev.updateStateOnServer('deviceEnteredGeo', value=iDevGeoName)
                                    dev.updateStateOnServer('deviceInNestRange', value=iDevNestRange)
                                    if iTracking:
                                        indigo.server.log(iDevName+' has entered GeoFence '+iDevGeoName)

                                elif iDevGeoInRange == 'false':
                                    dev.updateStateOnServer('deviceInGeoRange', value='false')
                                    dev.updateStateOnServer('deviceEntered', value= 'false')
                                    dev.updateStateOnServer('deviceLeft', value = 'true')
                                    dev.updateStateOnServer('deviceLeftGeo', value=iOldGeoName)
                                    dev.updateStateOnServer('deviceEnteredGeo', value='')
                                    dev.updateStateOnServer('deviceInNestRange', value='false')

                                    if iTracking:
                                        indigo.server.log(iDevName+' has left GeoFence '+iOldGeoName)

                        iRefDistanceShort = round(iRefDistance, iDecimal)
                        dev.updateStateOnServer('deviceGeoDistance', value=iRefDistanceShort)

                        # Create and store display version
                        # What are the units?

                        try:
                            if gUnits=='Imperial':
                                iDisplayVersion = miles_to_MilesFeet(iGeoDistance0,2,False)
                            elif gUnits == 'Metric':
                                iDisplayVersion = kilometres_to_KmMetres(iGeoDistance0,2,False)
                            else:
                                iDisplayVersion = str(round(iGeoDistance0, iDecimal))+' m'

                            dev.updateStateOnServer('geoDistanceDisplay', value=iDisplayVersion)
                        except:
                            errorHandler('iGeoLocation')

                    except:
                        errorHandler('iGeoLocation')
                        if iDebug2:
                            indigo.server.log(u'Failed to update device:'+dev.name)
                            iIssues = True
                    try:
                        # Calculate degree bearing from Home
                        # Debug messages on iDebug1
                        if iDebug1:
                            indigo.server.log('Trying to calculate bearings now for '+str(dev.name))
                            indigo.server.log('Values for Home are:'+str(iHome[0])+ ' '+str(iHome[1]))

                        if iHome[0]:
                            iHomeDev = indigo.devices[iHome[1]]
                            homeProps = iHomeDev.pluginProps
                            iReady1 = False
                            iReady2 = False

                            if iDebug1:
                                indigo.server.log('iHome is true and is sited at '+str(iHomeDev.name))


                            if 'geoLatitude' in homeProps and 'geoLongitude' in homeProps:
                                if iDebug1:
                                    indigo.server.log('Home geofence Values exist:'+str(homeProps['geoLatitude'])+ ' and '+str(homeProps['geoLongitude']))

                                if homeProps['geoLatitude'] != 0.0 and homeProps['geoLongitude'] != 0.0:
                                    iHomeLatLong = float(homeProps['geoLatitude']), float(homeProps['geoLongitude'])
                                    iReady1 = True
                            else:
                                if iDebug1:
                                    indigo.server.log('No Home Geo Long/Lat data available for '+str(iHomeDev.name), isError = True)
                                    indigo.server.log('Please check GeoFence settings for Longitude and Latitude', isError = True)
                                    indigo.server.log('Home distance calculation aborted')
                                    continue

                            if iDebug1:
                                indigo.server.log('Device Values for Lat & Long are:'+str(dev.states['deviceLatitude'])+ ' and '+str(dev.states['deviceLongitude']))

                            if dev.states['deviceLatitude'] !="0" and dev.states['deviceLongitude'] !="0" and len(
                                    dev.states['deviceLatitude']) != 0 and len(dev.states['deviceLongitude']) != 0:
                                iReady2 = True
                                iDevLatLong = float(dev.states['deviceLatitude']), float(dev.states['deviceLongitude'])
                            else:
                                if iDebug1:
                                    indigo.server.log('Something is not correct with geo settings for device '+str(dev.name), isError = True)
                                    indigo.server.log('Please check Device setting for Longitude and Latitude', isError = True)
                                    indigo.server.log('Home distance calculation aborted')
                                    continue

                            # Calculate Bearing
                            if iDebug1:
                                indigo.server.log('Ok now for the bearing...'+str(iHomeLatLong)+' '+str((iDevLatLong)))

                            if iReady1 and iReady2:
                                iBearing = iCompass(iHomeLatLong, iDevLatLong)
                                iDegree = iBearing[0]
                                iCPoint = iBearing[1]

                                if iDebug1:
                                    indigo.server.log('Bearings...'+str(iBearing))
                            else:
                                iDegree = 0.0
                                iCPoint = "n/a"

                            # Now the distance to Home
                            iDistanceHome = iDistance(iHomeLatLong[0],iHomeLatLong[1],iDevLatLong[0], iDevLatLong[1])

                            #Convert to the right units
                            iDistanceToHome = convertUnits(iDistanceHome[1])
                            iDistanceShort0 = round(iDistanceToHome[0],iDecimal)
                            iDistanceShort1 = round(iDistanceToHome[1],iDecimal)


                            if iDebug1:
                                indigo.server.log('Distance Home (m)...'+str(iDistanceHome))

                            # User wants to use google to calculate the actual distance
                            if iUseRealDistance:
                                origin = iHomeLatLong[0],iHomeLatLong[1]
                                destination = iDevLatLong[0], iDevLatLong[1]
                                iRealDistanceHome = distanceCalculation(origin, destination, mapAPI, iUseRealDistanceMode, "metric")
                                if len(iRealDistanceHome[1]) != 0 and iRealDistanceHome[0] != 'FailAPI':
                                    try:
                                        iRealDistanceVal = int(float((iRealDistanceHome[1][:-2]).strip()))
                                    except ValueError:
                                        errorHandler('iGeoLocation')
                                        iRealDistanceVal = 0.0


                                    # Now convert
                                    if gUnits=='Imperial':
                                        if iRealDistanceHome[1].find('k') != -1:
                                            iRealDistanceVal = float(iRealDistanceVal) * 0.621371192 # Km to miles conversion
                                            iRealDistanceDisplay = miles_to_MilesFeet(iRealDistanceVal,2,False)
                                        else:
                                            iRealDistanceVal = float(iRealDistanceVal) * 0.000621371192 # m to miles conversion
                                            iRealDistanceDisplay = miles_to_MilesFeet(iRealDistanceVal,2,False)

                                    elif gUnits == 'Metric':
                                        if iRealDistanceHome[1].find('k') != -1:
                                            iRealDistanceDisplay= kilometres_to_KmMetres(iRealDistanceVal,2,False)
                                        else:
                                            iRealDistanceDisplay= kilometres_to_KmMetres(float(iRealDistanceVal)/1000.0,2,False)
                                    else:
                                        if iRealDistanceHome[1].find('k') != -1:
                                            iRealDistanceDisplay = str(iRealDistanceVal*1000.0)+' m'
                                        else:
                                            iRealDistanceDisplay = str(iRealDistanceVal)+' m'

                                    if iRealDistanceDisplay != '0.0 m':
                                        dev.updateStateOnServer('realDistanceHome', value = iRealDistanceDisplay)
                                        dev.updateStateOnServer('realTimeHome', value = iRealDistanceHome[0])
                                    else:
                                        dev.updateStateOnServer('realDistanceHome', value = "** No Google Route Home **")
                                        dev.updateStateOnServer('realTimeHome', value = iRealDistanceHome[0])
                                else:
                                    dev.updateStateOnServer('realDistanceHome', value = '')
                                    dev.updateStateOnServer('realTimeHome', value = '')

                            dev.updateStateOnServer('directionDegree', value=iDegree)
                            dev.updateStateOnServer('directionCompass', value=iCPoint)
                            dev.updateStateOnServer('geoHomeName', value = iHome[2])
                            dev.updateStateOnServer('distanceHome', value = iDistanceShort0)

                            # Create and store display version
                            # What are the units?
                            if gUnits=='Imperial':
                                iDisplayVersion = miles_to_MilesFeet(iDistanceShort0,2,False)
                            elif gUnits == 'Metric':
                                iDisplayVersion = kilometres_to_KmMetres(iDistanceShort0,2,False)
                            else:
                                iDisplayVersion = str(iDistanceShort0)+' m'

                            dev.updateStateOnServer('geoHomeDistanceDisplay', value=iDisplayVersion)

                        else:
                            dev.updateStateOnServer('directionDegree', value=0.0)
                            dev.updateStateOnServer('directionCompass', value='n/a')
                            dev.updateStateOnServer('geoHomeName', value= 'n/a')
                            dev.updateStateOnServer('distanceHome', value=0.0)
                            dev.updateStateOnServer('geoHomeDistanceDisplay', value='')
                            dev.updateStateOnServer('realDistanceHome', value='')
                            dev.updateStateOnServer('realTimeHome', value='')
                    except:
                        errorHandler('iGeoLocation')
                        if iDebug1:
                            indigo.server.log(u'Failed to calculate bearing numbers or update correctly - advise Developer')

                else:
                    dev.updateStateOnServer('deviceNearestGeoName', value = 'No Location Found')
                    dev.updateStateOnServer('deviceGeoDistance', value = str(0))
                    dev.updateStateOnServer('geoDistanceDisplay', value='')
                    dev.updateStateOnServer('deviceInGeoRange', value = 'false')
                    dev.updateStateOnServer('deviceInNestRange', value = 'false')
                    dev.updateStateOnServer('deviceEntered', value='false')
                    dev.updateStateOnServer('deviceLeft', value='false')
                    dev.updateStateOnServer('directionDegree', value=0.0)
                    dev.updateStateOnServer('directionCompass', value='n/a')
                    dev.updateStateOnServer('geoHomeName', value='Unknown')
                    dev.updateStateOnServer('geoHomeDistanceDisplay', value='')
                    dev.updateStateOnServer('realDistanceHome', value='')
                    dev.updateStateOnServer('realTimeHome', value='')

                    if iTracking:
                        indigo.server.log(iDevName+' cannot be located')
            except:
                errorHandler('iGeoLocation '+dev.name)
                if iDebug1:
                    indigo.server.log(u'Failed to update Apple Device:'+dev.name+u' reason unknown')
                pass

            try:
                # Finally update the geoDevice States with device presence information
                for geo in indigo.devices.iter('self.iGeoFence'):
                    newProps = geo.pluginProps
                    if not 'geoName' in newProps:
                        # Device being created so ignore
                        continue
                    try:
                        if not newProps['geoActive']:
                            if iDebug3:
                                indigo.server.log(u'GeoFence '+newProps['geoName']+u' is inactive so ignored')

                            # Update Geo states
                            geo.updateStateOnServer('devicesNear', value = str(0))
                            geo.updateStateOnServer('devicesInRange', value = str(0))
                            geo.updateStateOnServer('devicesInNestRange', value = str(0))
                            geo.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                            continue
                        else:
                            geo.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                            if False:
                                indigo.server.log(u'GeoFence '+newProps['geoName']+u' is active')

                    except:
                        errorHandler('iGeoLocation '+geo.name)
                        if iDebug1:
                            indigo.server.log(u'Failed to determine state of GeoFence - check with Developer')

                    igeoName = newProps['geoName']
                    iRange = 0
                    iNest = 0
                    iNear = 0

                    for iCheck in indigo.devices.iter('self.iAppleDeviceAuto'):
                        idevProps = iCheck.pluginProps
                        if iCheck.states['deviceNearestGeoName'] == igeoName:
                            # It's near this one...
                            iNear += 1

                            # Is it a NEST Management Device?
                            if 'nestMode' in idevProps:
                                if not idevProps['nestMode']:
                                    # Device does not manage NEST Geos so not in Range
                                    iCheck.updateStateOnServer('deviceInNestRange', 'false')
                            else:
                                # Device management not specified there doesn't manage NESTs
                                iCheck.updateStateOnServer('deviceInNestRange', 'false')

                            if iCheck.states['deviceInNestRange'] == 'true':
                                iNest += 1

                            if iCheck.states['deviceInGeoRange'] == 'true':
                                iRange += 1

                    try:
                        # Update Geo states
                        if geo.states['devicesNear'] != str(iNear):
                            geo.updateStateOnServer('devicesNear', value = str(iNear))
                        if geo.states['devicesInRange'] != str(iRange):
                            geo.updateStateOnServer('devicesInRange', value = str(iRange))
                        if geo.states['devicesInNestRange'] != str(iNest):
                            geo.updateStateOnServer('devicesInNestRange', value = str(iNest))

                        localProps = geo.pluginProps

                        if not localProps['geoActive']:
                            geo.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                        else:
                            geo.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    except:
                        errorHandler('iGeoLocation '+geo.name)
                        if iDebug1:
                            indigo.server.log(u'Failed in GeoFence custom state updates calculations for GeoFence Device:'
                                              u''+geo.name+u' - advise Developer')
                        pass
            except:
                errorHandler('iGeoLocation '+geo.name)
                raise
                if iDebug1:
                    indigo.server.log(u'Failed in range calculations for GeoFence Device:'
                                      u''+geo.name+u' - advise Developer')
                pass

            # If we are tracking we need to take a snapshot of changes for tracking reporting
            # UMove will tell us if it's moved or not
            if iTrackHistory and dev.states['UMoved'] and dev.states['deviceActive'] == 'true' \
                    and dev.states['loggedTrack'] == 'false':

                # We are tracking and it's moved beyond the trigger for stationary so record the new data in the database
                dev.updateStateOnServer('loggedTrack', value = 'true')

                iSnapshot = {}
                iSnapshot['name'] = dev.name
                iSnapshot['lat'] = dev.states['deviceLatitude']
                iSnapshot['lon'] = dev.states['deviceLongitude']
                iSnapshot['add'] = dev.states['deviceAddress']
                iSnapshot['geoName'] = dev.states['deviceNearestGeoName']
                iSnapshot['geoRange'] = dev.states['deviceInGeoRange']
                iSnapshot['geoHome'] = dev.states['geoHomeName']
                iSnapshot['homeDist'] = dev.states['geoHomeDistanceDisplay']
                iSnapshot['timestamp'] = time.time()
                db.insert(iSnapshot)

    except:
        errorHandler('iGeoLocation - General Failure')
        if iDebug1:
            indigo.server.log(u'General failure in Geofence calculations - advise Developer')
        pass

    return

def urlAllGenerate(mapAPIKey='No Key', iHorizontal=640, iVertical=640, iZoom=15):

    ################################################
    # Routine generate a Static Google Maps HTML URL request
    # for all devices
    # Map size is automatically calculated based on the two furthest points (devices and/or geofences)
    # All commands are of the format...
    # https://maps.googleapis.com/maps/api/staticmap?parameters where the parameters
    # Determine the map content and format
    # Parameters are separated with the & symbol
    # Need to take care of the piping symbol
    # url pipe = %7C

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, gIcon

    # Create geoFence list
    try:
        geoList = []
        for geo in indigo.devices.iter('self.iGeoFence'):
            geoProps=geo.pluginProps
            geoLat = geoProps['geoLatitude']
            geoLong = geoProps['geoLongitude']
            geoList.append((geoLat,geoLong))

        # Create Map url
        # URL Centre and Zoom is calculated by Google Maps
        mapCentre = ''

        # Set zoom
        mapZoom = ''

        # Set size
        if iHorizontal>640:
            iHorizontal=640
        elif iHorizontal<50:
            iHorizontal=50

        if iVertical>640:
            iVertical=640
        elif iVertical<50:
            iVertical=50

        mapSize='size='+str(iHorizontal)+'x'+str(iVertical)
        mapFormat='format=jpg'

        # Use a standard marker for a GeoFence Centre
        mapMarkerGeo = "markers=color:blue%7Csize:mid%7Clabel:G"

        # Now create the device markers (must be a maximum of 5 different types and less than 64x64 and on a http: server)
        mapMarkerP = ''
        mapMarkerPhone = ''
        for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
            devProps = dev.pluginProps

            if (not 'customIcon' in devProps) or len(devProps['customIcon']) == 0 or devProps['customIcon'] == 'None' \
                    or gIcon.find(devProps['customIcon']) == -1:

                mapMarkerP = "markers=icon:http://chart.apis.google.com/chart?chst=d_map_pin_icon%26chld=mobile%257CFF0000%7C"+\
                             str(dev.states['deviceLatitude'])+","+str(dev.states['deviceLongitude'])
            else:
                iCustomIcon = devProps['customIcon']
                mapMarkerP = "markers=icon:"+iCustomIcon+"%7C"+str(dev.states['deviceLatitude'])+","+str(dev.states['deviceLongitude'])

            # Store the custom marker
            mapMarkerPhone = mapMarkerPhone+'&'+mapMarkerP

        if len(mapMarkerPhone)<2:
            #Trap no devices
            mapMarkerPhone = ''

        mapGoogle = 'https://maps.googleapis.com/maps/api/staticmap?'
        for geoRange in range(len(geoList)):
            mapMarkerGeo = mapMarkerGeo+'%7C'+str(geoList[geoRange][0])+","+str(geoList[geoRange][1])

        if mapAPIKey == 'No Key':
            customURL = mapGoogle+mapCentre+'&'+mapZoom+'&'+mapSize+'&'+mapFormat+'&'+mapMarkerGeo+'&'+mapMarkerPhone
        else:
            customURL = mapGoogle+mapCentre+'&'+mapZoom+'&'+mapSize+'&'+mapFormat+'&'+mapMarkerGeo+'&'+mapMarkerPhone+'&key='+mapAPIKey

        return customURL

    except:
        errorHandler('urlAllGenerate')
        return ''

def urlGenerate(mobileLL=[], mapAPIKey='No Key', iHorizontal=600, iVertical=300, iZoom=15, dev=0):

    ################################################
    # Routine generate a Static Google Maps HTML URL request
    # for a single device
    # Map size is based on the zoom parameter passed or defaults to level 15 (street names)
    # All commands are of the format...
    # https://maps.googleapis.com/maps/api/staticmap?parameters where the parameters
    # Determine the map content and format
    # Parameters are separated with the & symbol
    # Need to take care of the piping symbol
    # url pipe = %7C

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

    # Create geoFence list
    try:
        geoList = []

        if iDebug2:
            indigo.server.log('** Device being mapped is:'+dev.name+' '+str(dev.states['deviceLatitude'])+' '+str(dev.states['deviceLongitude']))

        for geo in indigo.devices.iter('self.iGeoFence'):
            if iDebug4:
                indigo.server.log('** Geo being mapped is:'+geo.name)

            try:
                geoProps=geo.pluginProps
                geoLat = geoProps['geoLatitude']
                geoLong = geoProps['geoLongitude']
                geoList.append((geoLat,geoLong))

            except KeyError:
                # Ignore the error but report the GeoFence causing the issue to the developer and user
                indigo.server.log('ERROR - Problem accessing Lat & Long on GeoFence'+geo.name, isError = True)
                indigo.server.log('Check GeoFence configuration and Save again. Alternatively recreate GeoFence'
                                  'or contact the Developer', isError = True)
                continue

        # Create Map url
        mapCentre = 'center='+str(mobileLL[0][0])+","+str(mobileLL[0][1])

        # Set zoom
        if iZoom<0:
            iZoom = 0
        elif iZoom>21:
            iZoom = 21
        mapZoom = 'zoom='+str(iZoom)

        # Set size
        if iHorizontal>640:
            iHorizontal=640
        elif iHorizontal<50:
            iHorizontal=50

        if iVertical>640:
            iVertical=640
        elif iVertical<50:
            iVertical=50

        mapSize='size='+str(iHorizontal)+'x'+str(iVertical)
        mapFormat='format=jpg'

        # Use a standard marker for a GeoFence Centre
        mapMarkerGeo = "markers=color:blue%7Csize:mid%7Clabel:G"

        # Now create the device marker (must be less than 64x64 and on a http: server)
        devProps = dev.pluginProps
        if not 'customIcon' in devProps or len(devProps['customIcon']) == 0 or devProps['customIcon'] == 'None':
            mapMarkerPhone = "markers=icon:http://chart.apis.google.com/chart?chst=d_map_pin_icon%26chld=mobile%257CFF0000%7C"+str(mobileLL[0][0])+","+str(mobileLL[0][1])
        else:
            iCustomIcon = devProps['customIcon']
            mapMarkerPhone = "markers=icon:"+iCustomIcon+"%7C"+str(mobileLL[0][0])+","+str(mobileLL[0][1])

        mapGoogle = 'https://maps.googleapis.com/maps/api/staticmap?'
        for geoRange in range(len(geoList)):
            mapMarkerGeo = mapMarkerGeo+'%7C'+str(geoList[geoRange][0])+","+str(geoList[geoRange][1])

        if mapAPIKey == 'No Key':
            customURL = mapGoogle+mapCentre+'&'+mapZoom+'&'+mapSize+'&'+mapFormat+'&'+mapMarkerGeo+'&'+mapMarkerPhone
        else:
            customURL = mapGoogle+mapCentre+'&'+mapZoom+'&'+mapSize+'&'+mapFormat+'&'+mapMarkerGeo+'&'+mapMarkerPhone+'&key='+mapAPIKey
        return customURL
    except:
        errorHandler('urlGenerate')
        return ''

def updateDeviceMap(iMaps='', mapAPIKey='No Key', iHorizontal=600, iVertical=300, iZoom=15, dev=0, iTarget='iPhone'):

    ################################################
    # Routine generate a single Static Google Map from a formatted URL
    # for all devices.  This is a PNG file that can be used on Control Pages in Indigo
    # and is saved in the Maps directory specified by the user

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, gUnits
    try:
        # Updates individual maps for all devices
        # Set up map files
        iCustom = True
        iMapFiles = iMaps

        if iTarget=='iPhone':
            iTarget=''

        if len(iMapFiles) == 0:
            # Set to default
            iCustom = False
            iMapFiles = '/Library/Application Support/Perceptive Automation/Indigo 6/Plugins/iFindStuff.indigoPlugin/Contents/Server Plugin/pygmaps'

        # Now choose a device for plotting
        if dev.configured and dev.enabled and dev.states['deviceActive'] == 'true':
            if iCustom:
                iPrefix = dev.name
                iPrefix = iPrefix.encode('ascii', 'ignore')
                iPrefix = iPrefix.replace("'","")
                iPrefix = iPrefix+iTarget.upper()
            else:
                iPrefix = ''+iTarget.upper()

            # Now plot the device and all geofences
            if len(dev.states['deviceLatitude'])>0 and len(dev.states['deviceLongitude'])>0:
                iLatDevice = float(dev.states['deviceLatitude'])
                iLongDevice = float(dev.states['deviceLongitude'])
                iMobileLocation = []
                iMobileLocation.append((iLatDevice,iLongDevice))

            # There is a requirements for an API key
            drawUrl=urlGenerate(iMobileLocation, mapAPIKey, iHorizontal, iVertical, iZoom, dev)

            fileMap = ""

            if iDebug3:
                webbrowser.open_new(drawUrl)

            # Prepare the file and draw the map
            iFileName = iMapFiles+'/'+iPrefix.upper()+'.jpg'
            fileMap = "curl --output '"+iFileName+"' --url '"+drawUrl+"'"
            os.system(fileMap)
            if iDebug3:
                indigo.server.log('Saving Map...'+iFileName)
    except:
        errorHandler('updateDeviceMap')
    return

def updateAllDeviceMaps(iMaps='', mapAPIKey='No Key', iHorizontal=600, iVertical=300, iZoom=15, iTargetDevice='iPad'):

    ################################################
    # Routine generate a Static Google Map from a formatted URL
    # for all devices.  This is a PNG file that can be used on Control Pages in Indigo
    # and is saved in the Maps directory specified by the user

    global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, gUnits
    try:
        # Updates individual maps for all devices
        # Set up map files
        iCustom = True
        if iTargetDevice=='iPhone':
            iTargetDevice = ''

        iMapFiles = iMaps
        if len(iMapFiles) == 0:
            # Set to default
            iCustom = False
            iMapFiles = '/Library/Application Support/Perceptive Automation/Indigo 6/Plugins/iFindStuff.indigoPlugin/Contents/Server Plugin/pygmaps'

        for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
            # Now choose a device for plotting
            if dev.configured and dev.enabled and dev.states['deviceActive'] == 'true':
                if iCustom:
                    iPrefix = dev.name
                    iPrefix = iPrefix.encode('ascii', 'ignore')
                    iPrefix = iPrefix.replace("'","")
                    iPrefix = iPrefix+iTargetDevice.upper()
                else:
                    iPrefix = ''+iTargetDevice.upper()

                # Now plot the device and all geofences
                if len(dev.states['deviceLatitude'])>0 and len(dev.states['deviceLongitude'])>0:
                    iLatDevice = float(dev.states['deviceLatitude'])
                    iLongDevice = float(dev.states['deviceLongitude'])
                    iMobileLocation = []
                    iMobileLocation.append((iLatDevice,iLongDevice))

                # There is a requirements for an API key
                drawUrl=urlGenerate(iMobileLocation, mapAPIKey, iHorizontal, iVertical, iZoom, dev)

                fileMap = ""

                if iDebug4:
                    webbrowser.open_new(drawUrl)

                # Prepare the file and draw the map
                iFileName = iMapFiles+'/'+iPrefix.upper()+'.jpg'
                fileMap = "curl --output '"+iFileName+"' --url '"+drawUrl+"'"
                os.system(fileMap)
                if iDebug3:
                    indigo.server.log('Saving Map...'+iFileName)

        # Finally update the all devices map
        drawUrl = urlAllGenerate(mapAPIKey,iHorizontal,iVertical, iZoom)
        fileMap = ""

        if iDebug4:
            webbrowser.open_new(drawUrl)

        # Prepare the file and draw the map
        iFileName = iMapFiles+'/'+iTargetDevice.upper()+'ALLDEVICES.jpg'
        fileMap = "curl --output '"+iFileName+"' --url '"+drawUrl+"'"
        os.system(fileMap)
        if iDebug3:
            indigo.server.log('Saving Map...'+iFileName)

    except:
        errorHandler('updateAllDeviceMaps')

    return

def iConvert(oldUnits, newUnits):

    ################################################
    # Routine called to recalculate distances & ranges
    # when the units are changed in the iFindStuff configuration dialog

    # Select the right conversion
    global gUnits
    try:
        if oldUnits == newUnits:
            # No change
            return True

        else:
            # Conversion factors are: 1km = 0.6214 miles, 1m=3.2808 ft, 1m = 0.0006214 miles, 1ft = 0.3048m
            # 1ml = 1.609.344km, 1km = 0.6214ml
            # Fields for change are: deviceAccuracy, deviceGeoDistance, distanceHome, geoRange

            if oldUnits == 'Metres' and newUnits =='Metric':
                   iRangeConvert = 1.0
                   iDistanceConvert = 0.001

            elif oldUnits == 'Metres' and newUnits =='Imperial':
                   iRangeConvert = 3.2808
                   iDistanceConvert = 0.0006214

            elif oldUnits == 'Imperial' and newUnits =='Metres':
                   iRangeConvert = 0.3048
                   iDistanceConvert = 1609.344

            elif oldUnits == 'Imperial' and newUnits =='Metric':
                   iRangeConvert = 0.3048
                   iDistanceConvert = 1.609344

            elif oldUnits == 'Metric' and newUnits =='Metres':
                   iRangeConvert = 1.0
                   iDistanceConvert = 1000.0

            elif oldUnits == 'Metric' and newUnits =='Imperial':
                   iRangeConvert = 3.2808
                   iDistanceConvert = 0.6214

            for dev in indigo.devices.iter('self'):
                if dev.deviceTypeId == 'iAppleAccount':
                    # Ignore account devices
                    continue

                elif dev.deviceTypeId == 'iAppleDeviceAuto':
                    # Convert three fields
                    dev.updateStateOnServer('deviceAccuracy', value=str(float(dev.states['deviceAccuracy'])*iRangeConvert))
                    dev.updateStateOnServer('deviceGeoDistance', value=str(float(dev.states['deviceGeoDistance'])*iDistanceConvert))
                    dev.updateStateOnServer('distanceHome', value=str(float(dev.states['distanceHome'])*iDistanceConvert))

                elif dev.deviceTypeId == 'iGeoFence':
                    # Convert one field
                    deviceProps = dev.pluginProps
                    deviceProps['geoRange'] = int(float(deviceProps['geoRange'])*iRangeConvert)
                    dev.replacePluginPropsOnServer(deviceProps)
    except:
        errorHandler('iConvert')

    return True


################################################################################
class Plugin(indigo.PluginBase):
    ########################################

    ################################################
    # Start of plugin definition

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):

        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.validatePrefsConfigUi(pluginPrefs)

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, iDebug5
        global addAccountId
        global gUnits

        # Set up version checker
        iFindStuffVersionFile = 'https://www.dropbox.com/s/eax4tmk69glggkm/iFindStuffVersionInfo.html?dl=0'
        self.updater = indigoPluginUpdateChecker.updateChecker(self, iFindStuffVersionFile, 1)

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def validatePrefsConfigUi(self, valuesDict):
         return (True, valuesDict)

    def startup(self):

        ################################################
        # Called on startup or reset of the plugin.
        # It maintains the folder structure (multi or single)
        # for the plugin

        global gUnits, fingScanLink

        # Get fingscan status
        fingScanLink = self.pluginPrefs.get('fingscanLink', False)

        # Set the units
        gUnits = self.pluginPrefs.get('distanceUnits', 'Metres')

        for dev in indigo.devices.itervalues("self"):
            dev.stateListOrDisplayStateIdChanged()

        # Ensure all devices are locked
        for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
            devProps = dev.pluginProps
            devProps['accountLocked'] = 'true'
            devProps['deviceLocked'] = 'true'
            dev.replacePluginPropsOnServer(devProps)

            # Prepare OldLat for comparison first time round
            dev.updateStateOnServer('ULat', value = 0.0)
            dev.updateStateOnServer('ULong', value = 0.0)
            dev.updateStateOnServer('UMoved', value = True)
            dev.updateStateOnServer('oldLat', value=dev.states['deviceLatitude'])
            dev.updateStateOnServer('oldLong', value = dev.states['deviceLongitude'])

            if 'lastStationaryCheck' in dev.states:
                dev.updateStateOnServer('lastStationaryCheck', value = int(time.time()))

        try:
            iFolders = self.pluginPrefs.get('checkboxSingleFolder', False)
            if not iFolders:
                # Creates Standard Folders
                # Check if folder iFindStuff exists
                if not ('iFindStuff Accounts' in indigo.devices.folders):
                    # Create the folder
                    iFolderId = indigo.devices.folder.create("iFindStuff Accounts")

                if not ('iFindStuff Devices' in indigo.devices.folders):
                    # Create the folder
                    iFolderId = indigo.devices.folder.create("iFindStuff Devices")

                if not ('iFindStuff Inactive' in indigo.devices.folders):
                    # Create the folder
                    iFolderId = indigo.devices.folder.create("iFindStuff Inactive")

                if not ('iFindStuff GeoFences' in indigo.devices.folders):
                    # Create the folder
                    iFolderId = indigo.devices.folder.create("iFindStuff GeoFences")

                if ('iFindStuff' in indigo.devices.folders):
                    # Get the Id
                    iFolder = indigo.devices.folders.getId("iFindStuff")
                    indigo.devices.folder.delete(iFolder, deleteAllChildren=False)

            else:
                if not ('iFindStuff' in indigo.devices.folders):
                    # Create the folder
                    iFolderId = indigo.devices.folder.create("iFindStuff")
                if ('iFindStuff GeoFences' in indigo.devices.folders):
                    # Get the Id
                    iFolder = indigo.devices.folders.getId("iFindStuff GeoFences")
                    indigo.devices.folder.delete(iFolder, deleteAllChildren=False)
                if ('iFindStuff Inactive' in indigo.devices.folders):
                    # Get the Id
                    iFolder = indigo.devices.folders.getId("iFindStuff Inactive")
                    indigo.devices.folder.delete(iFolder, deleteAllChildren=False)
                if ('iFindStuff Accounts' in indigo.devices.folders):
                    # Get the Id
                    iFolder = indigo.devices.folders.getId("iFindStuff Accounts")
                    indigo.devices.folder.delete(iFolder, deleteAllChildren=False)
                if ('iFindStuff Devices' in indigo.devices.folders):
                    # Get the Id
                    iFolder = indigo.devices.folders.getId("iFindStuff Devices")
                    indigo.devices.folder.delete(iFolder, deleteAllChildren=False)

            if not iFolders:
                for dev in indigo.devices.iter("self"):
                    if dev.deviceTypeId == 'iAppleAccount':
                        if not ('iFindStuff Accounts' in indigo.devices.folders):
                            # Create the folder
                            iFolderId = indigo.devices.folder.create("iFindStuff Accounts")
                            iFolder = iFolderId.id
                        else:
                            iFolder = indigo.devices.folders.getId("iFindStuff Accounts")

                        indigo.device.moveToFolder(dev, value=iFolder)
                        dev.updateStateOnServer('accountActive', value = "Active")
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    if dev.deviceTypeId == 'iAppleDeviceAuto' and dev.states['deviceActive']=='true':
                        if not ('iFindStuff Devices' in indigo.devices.folders):
                            # Create the folder
                            iFolderId = indigo.devices.folder.create("iFindStuff Devices")
                            iFolder = iFolderId.id
                        else:
                            iFolder = indigo.devices.folders.getId("iFindStuff Devices")

                        indigo.device.moveToFolder(dev, value=iFolder)
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    if dev.deviceTypeId == 'iAppleDeviceAuto' and not dev.states['deviceActive']== 'true':
                        if not ('iFindStuff Inactive' in indigo.devices.folders):
                            # Create the folder
                            iFolderId = indigo.devices.folder.create("iFindStuff Inactive")
                            iFolder = iFolderId.id
                        else:
                            iFolder = indigo.devices.folders.getId("iFindStuff Inactive")

                        indigo.device.moveToFolder(dev, value=iFolder)
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                    if dev.deviceTypeId == 'iGeoFence':
                        geoProps = dev.pluginProps

                    if dev.deviceTypeId == 'iGeoFence' and geoProps['geoActive']:
                        if not ('iFindStuff GeoFences' in indigo.devices.folders):
                            # Create the folder
                            iFolderId = indigo.devices.folder.create("iFindStuff GeoFences")
                            iFolder = iFolderId.id
                        else:
                            iFolder = indigo.devices.folders.getId("iFindStuff GeoFences")

                        indigo.device.moveToFolder(dev, value=iFolder)
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                        localProps = dev.pluginProps

                    if dev.deviceTypeId == 'iGeoFence' and not geoProps['geoActive']:
                        if not ('iFindStuff Inactive' in indigo.devices.folders):
                            # Create the folder
                            iFolderId = indigo.devices.folder.create("iFindStuff Inactive")
                            iFolder = iFolderId.id
                        else:
                            iFolder = indigo.devices.folders.getId("iFindStuff Inactive")

                        indigo.device.moveToFolder(dev, value=iFolder)
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                        localProps = dev.pluginProps
            else:
                for dev in indigo.devices.iter("self"):

                    if not ('iFindStuff' in indigo.devices.folders):
                        # Create the folder
                        iFolderId = indigo.devices.folder.create("iFindStuff")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.devices.folders.getId("iFindStuff")

                    indigo.device.moveToFolder(dev, value=iFolder)

                    if dev.deviceTypeId == 'iGeoFence':
                        geoProps = dev.pluginProps

                    if dev.deviceTypeId == 'iAppleAccount':
                        dev.updateStateOnServer('accountActive', value = "Active")
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    if dev.deviceTypeId == 'iAppleDeviceAuto' and dev.states['deviceActive']=='true':
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    if dev.deviceTypeId == 'iAppleDeviceAuto' and not dev.states['deviceActive']== 'true':
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                    if dev.deviceTypeId == 'iGeoFence' and geoProps['geoActive']:
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                        localProps = dev.pluginProps

                    if dev.deviceTypeId == 'iGeoFence' and not geoProps['geoActive']:
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                        localProps = dev.pluginProps

        except:
            errorHandler('startup')
            if iDebug1:
                indigo.server.log(u'Failed to create standard directories - Indigo issue - advise Developer')

        try:
            if not ('iFindStuff' in indigo.variables.folders):
                # Create the folder
                iFolderId = indigo.variables.folder.create("iFindStuff")
                iFolder = iFolderId.id
            else:
                iFolder = indigo.variables.folders.getId("iFindStuff")

            # Create variables for frequency updates on triggers
            for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                # Create variables from the names of the devices removing ' and spaces
                iDevName = dev.name
                iDevName=iDevName.replace(" ","")
                iDevName=iDevName.replace("'","")
                iDevName=iDevName.encode('ascii', 'ignore')

                if not (iDevName.upper()+'FREQ' in indigo.variables):
                    # Need to create and initialise it
                    newVar = indigo.variable.create(iDevName.upper()+'FREQ', "600", iFolder)

        except:
            errorHandler('startup')
            if iDebug1:
                indigo.server.log(u'Failed to create iFindStuff variables - Indigo issue - advise Developer')

    def shutdown(self):
        if iDebug3:
            indigo.server.log(u"shutdown called")

    ########################################
    def runConcurrentThread(self):
        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, iDebug6, gCurrentAccount, gUnits, gIcon, iTrackHistory, db
        global errorFile

        # Get the most current information
        # Validate preferences exist
        try:
            iDebug1 = self.pluginPrefs.get('checkboxDebug1', False)
            iDebug2 = self.pluginPrefs.get('checkboxDebug2', False)
            iDebug3 = self.pluginPrefs.get('checkboxDebug3', False)
            iDebug4 = self.pluginPrefs.get('checkboxDebug4', False)
            iDebug5 = self.pluginPrefs.get('checkboxDebug5', False)
            iDebug6 = self.pluginPrefs.get('checkboxDebug6', True)
            iTrackHistory = self.pluginPrefs.get('checkboxTracking', True)
            iMapStore = self.pluginPrefs.get('mapStorage', '')
            iLogTime = self.pluginPrefs.get('logTime', "3600")
            iHistory = self.pluginPrefs.get('checkboxTracking', False)
            iTime = self.pluginPrefs.get('trackTime',"2")
            iTimeTrack = int(iTime)*3600*24 # trackTime is stored in days

            # Empty log
            f = open(errorFile,'w')
            f.write('#'*80+'\n')
            f.write('New Log:'+str(time.strftime(time.asctime()))+'\n')
            f.write('#'*80+'\n')
            f.close()
            logTimeNextReset = time.time()+int(iLogTime)

            if iTrackHistory:
                trackTimeNextReset = time.time()+int(iTimeTrack)
                try:
                    # Open the current tracking database
                    db = TinyDB(iMapStore+'/db.track')

                except:
                    errorHandler('runConcurrent - TinyDB access failed')

            gCurrentAccount = 0
            iUpdateCycle = 10
            iLoginCycle = 300
            iCountLogin = 0
            iUseRealDistanceInterval = 600
            iUseRealCount = iUseRealDistanceInterval
            iUseRealUpdateCycle = 10

        except:
            errorHandler('runConcurrent')
            if iDebug1:
                indigo.server.log(u'Failed to access pluginPrefs for iDebug1 - advise Developer')

        while True:
            # Apple API Plugin Configurations
            # Now refresh API and devices

            try:
                # Reset the log?
                if logTimeNextReset<time.time():
                    # Reset log
                    # Empty log
                    f = open(errorFile,'w')
                    f.write('#'*80+'\n')
                    f.write('Log reset:'+str(time.strftime(time.asctime()))+'\n')
                    f.write('#'*80+'\n')
                    f.close()
                    logReset = False
                    logTimeNextReset = time.time()+int(iLogTime)

                # Now process the devices
                iAPI = setupAPI()
                iFields = iCustomAPI()
                iTrackVar = self.pluginPrefs.get('refreshExt', False)
                iDebug1 = self.pluginPrefs.get('checkboxDebug1', False)
                iDebug2 = self.pluginPrefs.get('checkboxDebug2', False)
                iDebug3 = self.pluginPrefs.get('checkboxDebug3', False)
                iDebug4 = self.pluginPrefs.get('checkboxDebug4', False)
                iDebug5 = self.pluginPrefs.get('checkboxDebug5', False)
                iDebug6 = self.pluginPrefs.get('checkboxDebug6', False)
                iTrackHistory = self.pluginPrefs.get('checkboxTracking', True)
                iTracking = self.pluginPrefs.get('checkboxTrack', False)
                iMapStore = self.pluginPrefs.get('mapStorage', '')
                iMapFrequency = int(self.pluginPrefs.get('mapFrequency', "600"))
                iMapAutoSave = self.pluginPrefs.get('checkboxUpdateMaps', False)
                iTime = self.pluginPrefs.get('trackTime',"2")
                iTimeTrack = int(iTime)*3600*24 # trackTime is stored in days
                iLoginFails = 0
                fingScanLink = self.pluginPrefs.get('fingscanLink', False)

                # Scan tracking and remove old records if tracking
                if iTrackHistory:
                    iTrackCheck = time.time()-trackTimeNextReset
                    iTrackDeleteIds = []
                    for recordsProcessed in db.all():
                        if recordsProcessed['timestamp']<iTrackCheck:
                            # Record is out of date so record for deletion
                            iTrackDeleteIds.append(recordsProcessed.eid)

                    # Delete any old records
                    db.remove(eids=iTrackDeleteIds)

                # Form of measurement from configuration
                nUnits = self.pluginPrefs.get('distanceUnits', "Metres")

                # Create plugin flags for external use
                if nUnits == 'Metres':
                    nRange = 'metres'
                    nDistance = 'metres'

                elif nUnits == 'Metric':
                    nRange = 'metres'
                    nDistance = 'kilometres'
                else:
                    nRange = 'feet'
                    nDistance = 'miles'

                # Store preferences in configuration
                self.pluginPrefs['rangeMeasure'] = nRange
                self.pluginPrefs['distanceMesure'] = nDistance

                if nUnits != gUnits:
                    # Need to convert numbers to new distance units
                    indigo.server.log('Changing units to '+nUnits+'...')
                    iConvert(gUnits,nUnits)
                    gUnits = nUnits

                # Prepare for new calculation options
                iDecimal = self.pluginPrefs.get('decimalPlaces', 2)
                mapAPI = self.pluginPrefs.get('mapAPIKey', 'No Key')
                iUseRealDistance = self.pluginPrefs.get('realDistance', False)
                iUseRealDistanceMode = self.pluginPrefs.get('realDistanceMode',"driving")

                # Prepare trap string for graphics (Static only allows 5 custom icons)
                gIcon = ''
                for icon in range(1,5):
                    iTemp = self.pluginPrefs.get('customIcon'+str(icon),'Default')
                    if iTemp != 'None':
                        gIcon = gIcon+'****'+iTemp


            except:
                errorHandler('runConcurrent')
                if iDebug1:
                    indigo.server.log(u'Failed to access pluginPrefs for key fields - advise Developer')

            # Get the current time for comparision
            iNow = int(time.mktime(time.localtime()))
            iMapUpdate = iNow

            for dev in indigo.devices.iter("self.iAppleDeviceAuto"):
                # Get the current time for comparision
                iNow = int(time.mktime(time.localtime()))

                try:
                    if dev.configured and dev.enabled:

                        # Enable unit measures
                        if gUnits == 'Metres':
                            gRange = 'metres'
                            gDistance = 'metres'

                        elif nUnits == 'Metric':
                            gRange = 'metres'
                            gDistance = 'kilometres'
                        else:
                            gRange = 'feet'
                            gDistance = 'miles'

                        if dev.states['rangeUnits'] != gRange:
                            dev.updateStateOnServer('rangeUnits', value = gRange)

                        if dev.states['distanceUnits'] != gDistance:
                            dev.updateStateOnServer('distanceUnits', value = gDistance )

                        # Are we ready to update this device?
                        devProps = dev.pluginProps
                        iTimeCompare = dev.states['timeNextUpdate']

                        if iTimeCompare >= iNow:

                            if iDebug3:
                                if dev.states['deviceActive'] != 'false':
                                    iDiff = int(iNow - dev.states['timeNextUpdate'])
                                    indigo.server.log('Did not update: '+dev.name+' on this occasion but will in about'+str(iDiff)+'s')
                            # Still have to wait
                            # So move onto the next device
                            continue
                        else:
                            if iDebug3:
                                if dev.states['deviceActive'] != 'false':
                                    indigo.server.log('Updating: '+dev.name+' this time')

                        if dev.states['deviceActive'] == "false":
                            # Device isn't active so ignore
                            if iDebug3:
                                indigo.server.log('Device:'+dev.name+' is inactive so not updated...')

                            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                            continue

                        # Get the account device details
                        try:
                            iAccountDev = int(dev.states['deviceAccount'])
                            account = indigo.devices[iAccountDev]

                        except:
                            errorHandler('runConcurrent '+dev.name)
                            if iDebug1:
                                indigo.server.log('Could not find Account '+str(dev.states['deviceAccount'])
                                                  +' - check device '+str(dev.name))
                            # Couldn't find account
                            continue

                        accountProps = account.pluginProps
                        iUsername = accountProps["appleId"]
                        iPassword = accountProps["applePwd"]
                        iDevName = dev.name
                        iDevId = dev.id
                        iDevKey = dev.states['deviceUniqueKey']
                        iAccountId = account.id
                        iAccountName = account.name

                        # Map the device
                        iMap = iMapping(iUsername, iPassword, iAccountName, iAccountId, iDevName, iDevKey, iDevId)

                        if iMap[0] == 0 or iMap[0] == 2:
                            # If iMap[0] == 0 then all Ok, if iMap[0] == 2 it's ok but data wasn't read from device
                            # Must have logged in and tried to update the device without issue
                            if iMap[0] == 2:
                                # Didn't get any details off the phone so update states accordingly
                                dev.updateStateOnServer('batteryOnCharge','** Unknown Phone Offline **')
                                dev.updateStateOnServer('deviceAddress', '** Unknown Phone Offline **')
                                dev.updateStateOnServer('deviceBatteryLevel', '0')
                                dev.updateStateOnServer('deviceGeoDistance', '0')
                                dev.updateStateOnServer('deviceInGeoRange', 'false')
                                dev.updateStateOnServer('deviceInNestRange', 'false')
                                dev.updateStateOnServer('deviceNearestGeoName', 'Offline')
                                dev.updateStateOnServer('distanceHome', '0')
                                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                            iLoginFails = 0

                            # Now recalculate the next update time
                            # Work out when to recalculate

                            # Get the current time for comparision
                            iNow = int(time.mktime(time.localtime()))

                            if iDebug2:
                                indigo.server.log(u'Working out the next time for update for:' + dev.name)

                            if iMap[0] == 2:
                                # Failed Read - reschedule for default refresh rate
                                devProps = dev.pluginProps
                                iAddTime = int(devProps['frequencyTimer'])

                            else:
                                devProps = dev.pluginProps
                                if 'deviceVariableFrequency' in devProps:
                                    if iDebug3:
                                        indigo.server.log(u'Checking device frequency (1):'+unicode(devProps['deviceVariableFrequency']))

                                    if devProps['deviceVariableFrequency']:

                                        if iDebug3:
                                            indigo.server.log(u'Checking device frequency (2)')

                                        iDevName = dev.name
                                        iDevName=iDevName.replace(" ","")
                                        iDevName=iDevName.replace("'","")
                                        iDevName=iDevName.encode('ascii', 'ignore')
                                        iDevName=iDevName.upper()+'FREQ'
                                        iAddTime = int(indigo.variables[iDevName].value)
                                        if dev.states['calculateMethod'] != 'Variable':
                                            dev.updateStateOnServer('calculateMethod', value = 'Variable')
                                    else:
                                        iAddTime = nextUpdateCalc(dev)
                                        if dev.states['calculateMethod'] != 'Calculated':
                                            dev.updateStateOnServer('calculateMethod', value = 'Calculated')
                                else:
                                    iAddTime = nextUpdateCalc(dev)
                                    if dev.states['calculateMethod'] != 'Calculated':
                                        dev.updateStateOnServer('calculateMethod', value = 'Calculated')

                            if iDebug3:
                                indigo.server.log(u'Calculation complete:' + dev.name +u' update value'+str(iAddTime))

                            iUpdateTime = iNow + iAddTime

                            # Store it into the device
                            dev.updateStateOnServer('timeNextUpdate', value=iUpdateTime)
                            dev.updateStateOnServer('timeUpdateRead',
                                                    value=time.asctime(time.localtime(int(iUpdateTime))))
                            if iDebug3:
                                indigo.server.log('Details from update:'+dev.name+' '+str(iAddTime)+' '+str(iNow)+' '+str(iUpdateTime)+' '+dev.states['timeUpdateRead'])

                        elif iMap[0] == 1:
                            # Failed login
                            if iDebug1:
                                indigo.server.log('Failed login...'+str(iMap[1]), type='iFindStuff Critical ', isError=True)

                            if iMap[1] == 'NL':
                                iLoginFails += 1
                                indigo.server.log(u'Failed to access iDevice API on device'
                                                  u''+iDevName+u' - MAIN THREAD will try once more then terminate',isError=True)
                                if iLoginFails>2:
                                    indigo.server.log(u'Maximum number of login attempts tried',isError=True)
                                    indigo.server.log(u'Please check your username and '
                                                      u'password on the Apple Account Device before enabling again', isError=True)
                                    indigo.server.log(u'Terminating plugin', isError=True)
                                    break
                except:
                    errorHandler('runConcurrent')
                    if iDebug1:
                        indigo.server.log(u'Code failure while attempting to update devices - MT')

            # Now check the Geolocations for each device
            # Check that we only update Real Distance every 10 mins
            try:
                iUseRealCount = iUseRealCount + iUseRealUpdateCycle
                if iUseRealCount >= iUseRealDistanceInterval and iUseRealDistance:
                    # We can now update the real values (only 2500 allowed per day so we check every 10 mins)
                    iUseRealCount = 0
                    iUseReal = True
                else:
                    iUseReal = False

                iGeoLocation(iTracking, mapAPI, iDecimal, iUseReal, iUseRealDistanceMode)

            except:
                errorHandler('runConcurrent')

            # Update maps?
            try:
                if iMapAutoSave:
                    if iMapUpdate<iNow:
                        # Update the maps
                        # Get the API key (if it exists)
                        mapAPI = self.pluginPrefs.get('mapAPIKey', 'No Key')
                        iPadMaps = self.pluginPrefs.get('iPadMaps', False)
                        iPadMapHorizon = int(self.pluginPrefs.get('iPadMapHorizon', '640'))
                        iPadMapVertical=int(self.pluginPrefs.get('iPadMapVertical', '320'))
                        iPadMapZoom = int(self.pluginPrefs.get('iPadMapZoom', '15'))
                        iPhoneMaps = self.pluginPrefs.get('iPhoneMaps', False)
                        iPhoneMapHorizon = int(self.pluginPrefs.get('iPhoneMapHorizon', '320'))
                        iPhoneMapVertical=int(self.pluginPrefs.get('iPhoneMapVertical', '160'))
                        iPhoneMapZoom = int(self.pluginPrefs.get('iPhoneMapZoom', '15'))

                        # Update the maps
                        if iPadMaps:
                            mapAll = updateAllDeviceMaps(iMapStore, mapAPI, iPadMapHorizon, iPadMapVertical, iPadMapZoom, 'iPad')
                            if iDebug2:
                                indigo.server.log('iPad Maps refreshed for all devices...')

                        if iPhoneMaps:
                            mapAll = updateAllDeviceMaps(iMapStore, mapAPI, iPhoneMapHorizon, iPhoneMapVertical, iPhoneMapZoom, 'iPhone')
                            if iDebug2:
                                indigo.server.log('iPhone Maps refreshed for all devices...')
            except:
                errorHandler('runConcurrent')

             # Re login for token?
            try:
                iCountLogin = iCountLogin + iUpdateCycle
                if iCountLogin > iLoginCycle:
                    # Will need to login again
                    iCountLogin = 0
                    gCurrentAccount = 0
            except:
                errorHandler('runConcurrent')

            # Wait until the next time!
            self.sleep(iUpdateCycle)

        ######## Allow plugin to terminate gracefully
        indigo.server.log(u'Terminating iFindStuff Plugin...')
        self.shutdown()

    ########################################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):

        try:
            if typeId == 'iAppleAccount':
                errorDict = indigo.Dict()
                if 'appleId' in valuesDict:
                    iFail = False
                    if len(valuesDict['appleId']) == 0:
                        # Blank username!
                        iFail = True
                        errorDict["appleId"] = "No username entered"
                        errorDict["showAlertText"] = "You must obtain a valid Apple Account Username before installing this plugin"

                    elif valuesDict['appleId'].find('@') == -1:
                        # Not an email address as no @ symbol
                        iFail = True
                        errorDict["appleId"] = "Invalid email address as user name"
                        errorDict["showAlertText"] = "Username doesn't appear to be an email address"

                    if iFail:
                        return (False, valuesDict, errorDict)

                else:
                    return False, valuesDict

                if 'applePwd' in valuesDict:
                    iFail = False
                    if len(valuesDict['applePwd']) == 0:
                        # Blank password!
                        iFail = True
                        errorDict["applePwd"] = "No password entered"
                        errorDict["showAlertText"] = "You must enter a valid Apple Account password"

                    if iFail:
                        indigo.server.log("applePwd failed")
                        return (False, valuesDict, errorDict)

                if 'applePwd' in valuesDict and 'appleId' in valuesDict:


                    # Validate login
                    iLogin = iAuthorise(valuesDict['appleId'], valuesDict['applePwd'])
                    if not iLogin[0] == 0:

                        # Failed login
                        iFail = True
                        errorDict["appleId"] = "Could not log in with that username/password combination"
                        errorDict["showAlertText"] = "Login validation failed - check username & password or internet connection"

                    else:
                        # Get account details
                        api = iLogin[1]
                        dev = indigo.devices[devId]
                        iAccountNumber = str(dev.id)
                        dev.updateStateOnServer('accountActive',value = "Active")
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                        # Devices in or added to Dictionary so return OK
                        return True, valuesDict

                    if iFail:
                        indigo.server.log("Login to Apple Server Failed")
                        return (False, valuesDict, errorDict)


            elif typeId == 'iGeoFence':
                errorDict = indigo.Dict()
                if 'geoName' in valuesDict:
                    iFail = False
                    if len(valuesDict['geoName']) == 0:
                        # Blank name!
                        iFail = True
                        errorDict["geoName"] = "No location entered"
                        errorDict["showAlertText"] = "You must enter a valid and unique GeoFence name"

                    if iFail:
                        return (False, valuesDict, errorDict)

                if 'geoRange' in valuesDict:
                    iFail = False
                    if valuesDict['geoRange'] == 0:
                        # Blank range!
                        iFail = True
                        errorDict["geoName"] = "No range entered"
                        errorDict["showAlertText"] = "You must enter a valid range which is greater than 0"

                    if iFail:
                        return (False, valuesDict, errorDict)

                if devId != 0:
                    dev = indigo.devices[devId]

                    # Get default lat/long for indigo server
                    latLong=indigo.server.getLatitudeAndLongitude()
                    lat = latLong[0]
                    lng = latLong[1]
                    geoProps = dev.pluginProps

                    if 'geoLatitude' in geoProps:
                        if float(geoProps['geoLatitude']) == 0.0:
                            dev.updateStateOnServer('geoLatitude', value=lat)

                    if 'geoLongitude' in geoProps:
                        if float(geoProps['geoLongitude']) == 0.0:
                            dev.updateStateOnServer('geoLongitude', value=lng)

            elif typeId == 'iAppleDeviceAuto':

                if devId != 0:
                    dev = indigo.devices[devId]
                    iNow = int(time.mktime(time.localtime()))

                    # Check default fields for new devices
                    if 'stationaryMode' in valuesDict:
                        if not 'speedStation' in valuesDict:
                            valuesDict['speedStation'] = '1'
                        if not 'distanceTime' in valuesDict:
                            valuesDict['distanceTime'] = '600'
                        if not 'distanceFrequency' in valuesDict:
                            valuesDict['distanceFrequency'] = '600'

                    # Check time ranges
                    iFail = False

                    if 'homeTime' in valuesDict:
                        validateTime = timeValidate(valuesDict['homeTime'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["homeTime"] = "Range is invalid:"+validateTime[1]

                    if 'nightTime' in valuesDict:
                        validateTime = timeValidate(valuesDict['nightTime'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["nightTime"] = "Range is invalid:"+validateTime[1]

                    if 'powerTime' in valuesDict:
                        validateTime = timeValidate(valuesDict['powerTime'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["powerTime"] = "Range is invalid:"+validateTime[1]

                    if 'scheduleTime1' in valuesDict:
                        validateTime = timeValidate(valuesDict['scheduleTime1'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["scheduleTime1"] = "Range is invalid:"+validateTime[1]

                    if 'scheduleTime2' in valuesDict:
                        validateTime = timeValidate(valuesDict['scheduleTime2'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["scheduleTime2"] = "Range is invalid:"+validateTime[1]

                    if 'scheduleTime3' in valuesDict:
                        validateTime = timeValidate(valuesDict['scheduleTime3'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["scheduleTime3"] = "Range is invalid:"+validateTime[1]

                    if iFail:
                        errorDict["showAlertText"] = "The format of this field must be HH:MM-HH:MM in 24hr format"
                        return (False, valuesDict, errorDict)

                    if 'targetAccounts' in valuesDict:
                        dev.updateStateOnServer('deviceActive', value = "true")
                        dev.updateStateOnServer('deviceAccount', value=valuesDict['targetAccounts'])
                        dev.updateStateOnServer('timeNextUpdate', value=iNow)
                        dev.updateStateOnServer('timeUpdateRead', value=time.asctime(time.localtime(iNow)))
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                        # Now find the account name
                        for acc in indigo.devices.iter('iAppleAccount'):
                            if acc.id == int(valuesDict['targetAccounts']):
                                dev.updateStateOnServer('accountName', value=acc.name)
                                iAccountD = acc
                                break

                    # Now get the code
                    if 'targetDevices' in valuesDict:
                        if len(valuesDict['targetDevices']) != 0:
                            dev.updateStateOnServer('deviceUniqueKey', value=valuesDict['targetDevices'])
                        else:
                            valuesDict['targetDevices'] = dev.states['deviceUniqueKey']
                    else:
                        if iDebug1:
                            indigo.server.log('Could not find '+str(valuesDict('targetDevices')))

                    # Update the account code and update flag if editing
                    if len(dev.states['deviceAccount']) == 0:
                        dev.updateStateOnServer('deviceAccount', value=str(valuesDict['targetAccounts']))

                else:
                    # New device
                    iNow = int(time.mktime(time.localtime()))

                    # Check default fields for new devices
                    if 'stationaryMode' in valuesDict:
                        if not 'speedStation' in valuesDict:
                            valuesDict['speedStation'] = '1'
                        if not 'distanceTime' in valuesDict:
                            valuesDict['distanceTime'] = '600'
                        if not 'distanceFrequency' in valuesDict:
                            valuesDict['distanceFrequency'] = '600'

                    # Check time ranges
                    iFail = False

                    if 'homeTime' in valuesDict:
                        validateTime = timeValidate(valuesDict['homeTime'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["homeTime"] = "Range is invalid:"+validateTime[1]

                    if 'nightTime' in valuesDict:
                        validateTime = timeValidate(valuesDict['nightTime'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["nightTime"] = "Range is invalid:"+validateTime[1]

                    if 'powerTime' in valuesDict:
                        validateTime = timeValidate(valuesDict['powerTime'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["powerTime"] = "Range is invalid:"+validateTime[1]

                    if 'scheduleTime1' in valuesDict:
                        validateTime = timeValidate(valuesDict['scheduleTime1'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["scheduleTime1"] = "Range is invalid:"+validateTime[1]

                    if 'scheduleTime2' in valuesDict:
                        validateTime = timeValidate(valuesDict['scheduleTime2'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["scheduleTime2"] = "Range is invalid:"+validateTime[1]

                    if 'scheduleTime3' in valuesDict:
                        validateTime = timeValidate(valuesDict['scheduleTime3'])
                        if not validateTime[0]:
                            errorDict = indigo.Dict()
                            iFail = True
                            errorDict["scheduleTime3"] = "Range is invalid:"+validateTime[1]

                    if iFail:
                        errorDict["showAlertText"] = "The format of this field must be HH:MM-HH:MM in 24hr format"
                        return (False, valuesDict, errorDict)


            # All tests passed!
            return (True, valuesDict)

        except:
            errorHandler('validateDeviceConfigUI')
            if iDebug1:
                indigo.server.log(u'Failed to validate correctly - probable coding error - advise Developer')
                return False, valuesDict

    ########################################
    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        # When device dialog is closed we need to clean up any information or processes
        if userCancelled:
            pass

        if typeId == 'iAppleDeviceAuto':
            pass

    ########################################
    def deviceStartComm(self, dev):

        dev.stateListOrDisplayStateIdChanged()  # Ensure latest devices.xml is being used

        iSingle = self.pluginPrefs.get('checkboxSingleFolder', False)

        try:
            if dev.deviceTypeId == 'iAppleDeviceAuto':
                # Store the details in the dictionary
                if dev.configured and dev.enabled:
                    iKey = dev.states['deviceUniqueKey']
                    iData = dev.states['deviceAccount'],dev.states['timeNextUpdate']

                # Kick off an initial update
                # Get the current time for comparision
                    iNow = int(time.mktime(time.localtime()))
                    dev.updateStateOnServer('timeNextUpdate', value=iNow-10)
                    dev.updateStateOnServer('timeUpdateRead', value=time.asctime(time.localtime(iNow-10)))
                    if 'lastStationary' in dev.states:
                        dev.updateStateOnServer('lastStationary', value = 0)

                    deviceProps = dev.pluginProps
                    deviceProps['targetDevices'] = dev.states['deviceUniqueKey']
                    deviceProps['updateAccount'] = 'false'

                # Check defaults
                    try:
                        if len(deviceProps['frequencyTimer']) == 0:
                            deviceProps['frequencyTimer'] = '600'

                        if len(deviceProps['frequency50']) == 0:
                            deviceProps['frequency50'] = '600'

                        if len(deviceProps['frequency40']) == 0:
                            deviceProps['frequency40'] = '600'

                        if len(deviceProps['frequency30']) == 0:
                            deviceProps['frequency30'] = '600'
                    except:
                        errorHandler('deviceStartComm '+dev.name)
                        if iDebug1:
                            indigo.server.log(u'Failed to set Timer defaults on device:'+dev.name)
                    
                    # Check default fields for new fields
                    if 'stationaryMode' in deviceProps:
                        if not 'speedStation' in deviceProps:
                            deviceProps['speedStation'] = '1'
                        if not 'distanceTime' in deviceProps:
                            deviceProps['distanceTime'] = '600'
                        if not 'distanceFrequency' in deviceProps:
                            deviceProps['distanceFrequency'] = '600'

                    # Finally replace props on the device and create a variable
                    dev.replacePluginPropsOnServer(deviceProps)

                    if not ('iFindStuff' in indigo.variables.folders):
                        # Create the folder
                        iFolderId = indigo.variables.folder.create("iFindStuff")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.variables.folders.getId("iFindStuff")

                    # Create variable from the name of the device removing ' and spaces
                    iDevName = dev.name
                    iDevName=iDevName.replace(" ","")
                    iDevName=iDevName.replace("'","")
                    iDevName=iDevName.encode('ascii', 'ignore')

                    if not (iDevName.upper()+'FREQ' in indigo.variables):
                        # Need to create and initialise it
                        newVar = indigo.variable.create(iDevName.upper()+'FREQ', "60", iFolder)

            if dev.deviceTypeId == 'iGeoFence':
                if dev.configured and dev.enabled:
                    localProps = dev.pluginProps
                    iKey = dev.name
                    iData = localProps['geoActive'],localProps['geoHome']

            if not iSingle:
                if dev.deviceTypeId == 'iAppleAccount':
                    if not ('iFindStuff Accounts' in indigo.devices.folders):
                        # Create the folder
                        iFolderId = indigo.devices.folder.create("iFindStuff Accounts")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.devices.folders.getId("iFindStuff Accounts")

                    indigo.device.moveToFolder(dev, value=iFolder)
                    dev.updateStateOnServer('accountActive', value = "Active")
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                if dev.deviceTypeId == 'iAppleDeviceAuto' and dev.states['deviceActive']=='true':
                    if not ('iFindStuff Devices' in indigo.devices.folders):
                        # Create the folder
                        iFolderId = indigo.devices.folder.create("iFindStuff Devices")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.devices.folders.getId("iFindStuff Devices")

                    indigo.device.moveToFolder(dev, value=iFolder)
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                if dev.deviceTypeId == 'iAppleDeviceAuto' and not dev.states['deviceActive']== 'true':
                    if not ('iFindStuff Inactive' in indigo.devices.folders):
                        # Create the folder
                        iFolderId = indigo.devices.folder.create("iFindStuff Inactive")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.devices.folders.getId("iFindStuff Inactive")

                    indigo.device.moveToFolder(dev, value=iFolder)
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                if dev.deviceTypeId == 'iGeoFence':
                    geoProps = dev.pluginProps

                if dev.deviceTypeId == 'iGeoFence' and geoProps['geoActive']:
                    if not ('iFindStuff GeoFences' in indigo.devices.folders):
                        # Create the folder
                        iFolderId = indigo.devices.folder.create("iFindStuff GeoFences")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.devices.folders.getId("iFindStuff GeoFences")

                    indigo.device.moveToFolder(dev, value=iFolder)
                    localProps = dev.pluginProps
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                if dev.deviceTypeId == 'iGeoFence' and not geoProps['geoActive']:
                    if not ('iFindStuff Inactive' in indigo.devices.folders):
                        # Create the folder
                        iFolderId = indigo.devices.folder.create("iFindStuff Inactive")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.devices.folders.getId("iFindStuff Inactive")

                    indigo.device.moveToFolder(dev, value=iFolder)
                    localProps = dev.pluginProps
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

            else:

                if not ('iFindStuff' in indigo.devices.folders):
                    # Create the folder
                    iFolderId = indigo.devices.folder.create("iFindStuff")
                    iFolder = iFolderId.id
                else:
                    iFolder = indigo.devices.folders.getId("iFindStuff")

                indigo.device.moveToFolder(dev, value=iFolder)

                if dev.deviceTypeId == 'iAppleAccount':
                    dev.updateStateOnServer('accountActive', value = "Active")
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                if dev.deviceTypeId == 'iAppleDeviceAuto' and dev.states['deviceActive']=='true':
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                if dev.deviceTypeId == 'iAppleDeviceAuto' and not dev.states['deviceActive']== 'true':
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                if dev.deviceTypeId == 'iGeoFence':
                    geoProps = dev.pluginProps

                if dev.deviceTypeId == 'iGeoFence' and geoProps['geoActive']:
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                if dev.deviceTypeId == 'iGeoFence' and not geoProps['geoActive']:
                    localProps = dev.pluginProps
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

        except:
            errorHandler('deviceStartComm '+dev.name)
            if iDebug1:
                indigo.server.log(u'Attempt to move devices failed - advise Developer')

        try:
            if dev.deviceTypeId == 'iGeoFence':
                if dev.configured and dev.enabled:
                    localProps = dev.pluginProps
                    iKey = dev.name
                    iData = localProps['geoActive'],localProps['geoHome']

                    if 'geoName' in localProps:
                        # Update Name and Description!
                        dev.name = localProps['geoName']
                        dev.description = localProps['geoDescription']
                        dev.replacePluginPropsOnServer(localProps)

                        # Get default lat/long for indigo server
                        latLong=indigo.server.getLatitudeAndLongitude()
                        lat = latLong[0]
                        lng = latLong[1]

                    if 'geoLatitude' in localProps:
                        if float(localProps['geoLatitude']) == 0.0:
                            localProps['geoLatitude'] = lat

                    if 'geoLongitude' in localProps:
                        if float(localProps['geoLongitude']) == 0.0:
                            localProps['geoLongitude'] = lng

                    dev.replacePluginPropsOnServer(localProps)

                if 'geoActive' in dev.states:
                    if not localProps['geoActive']:
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                    else:
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

        except:
            errorHandler('deviceStartComm '+dev.name)
            if iDebug1:
                indigo.server.log(u'Failed to reset defaults for new Geofence - advise Developer')

    def deviceUpdated(self, origDev, newDev):
        try:
            localProps = newDev.pluginProps
            if 'geoActive' in localProps:
                if not localProps['geoActive']:
                    newDev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                else:
                    newDev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
        except:
            errorHandler('deviceUpdated '+newDev.name)
            if iDebug1:
                indigo.server.log(u'Failed to reset icon on device for Geofence - advise Developer')


    def deviceDeleted(self, dev):

        # Device deleted so we need to rebuild directory if it's a iDevice and delete any variables
        if dev.deviceTypeId == 'iAppleDeviceAuto':
            # Remove any variables for this device
            if not ('iFindStuff' in indigo.variables.folders):
                # Create the folder
                iFolderId = indigo.variables.folder.create("iFindStuff")
                iFolder = iFolderId.id
            else:
                iFolder = indigo.variables.folders.getId("iFindStuff")

            # Create variable from the name of the device removing ' and spaces
            iDevName = dev.name
            iDevName=iDevName.replace(" ","")
            iDevName=iDevName.replace("'","")
            iDevName=iDevName.encode('ascii', 'ignore')

            if iDevName.upper()+'FREQ' in indigo.variables:
                # Need delete it
                newVar = indigo.variable.delete(iDevName.upper()+'FREQ')

    def deviceStopComm(self, dev):
        # Called when communication with the hardware should be shutdown.
        pass

    ########################################
    # Sensor Action callback
    ######################
    def actionControlSensor(self, action, dev):
        ###### TURN ON ######
        # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
        if action.sensorAction == indigo.kSensorAction.TurnOn:
            if iDebug2:
                indigo.server.log(u"ignored \"%s\" %s request (device is read-only)" % (dev.name, "on"))

        ###### TURN OFF ######
        # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
        elif action.sensorAction == indigo.kSensorAction.TurnOff:
            if iDebug2:
                indigo.server.log(u"ignored \"%s\" %s request (device is read-only)" % (dev.name, "off"))

        ###### TOGGLE ######
        # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
        elif action.sensorAction == indigo.kSensorAction.Toggle:
            if iDebug2:
                indigo.server.log(u"ignored \"%s\" %s request (device is read-only)" % (dev.name, "toggle"))

    ########################################
    # General Action callback
    ######################
    def actionControlGeneral(self, action, dev):
        ###### BEEP ######
        if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
            # Beep the hardware module (dev) here:
            # ** IMPLEMENT ME **
            if iDebug2:
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

        ###### ENERGY UPDATE ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
            # Request hardware module (dev) for its most recent meter data here:
            # ** IMPLEMENT ME **
            if iDebug2:
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy update request"))

        ###### ENERGY RESET ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
            # Request that the hardware module (dev) reset its accumulative energy usage data here:
            # ** IMPLEMENT ME **
            if iDebug2:
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy reset request"))

        ###### STATUS REQUEST ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
            # Query hardware module (dev) for its current status here. This differs from the
            # indigo.kThermostatAction.RequestStatusAll action - for instance, if your thermo
            # is battery powered you might only want to update it only when the user uses
            # this status request (and not from the RequestStatusAll). This action would
            # get all possible information from the thermostat and the other call
            # would only get thermostat-specific information:
            # ** GET BATTERY INFO **
            # and call the common function to update the thermo-specific data
            self._refreshStatesFromHardware(dev)
            if iDebug2:
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))

    ########################################
    # Custom Plugin Action callbacks (defined in Actions.xml)
    ######################

    def selectIcon(self, filter="", valuesDict=None, typeId="", targetId=0):

        ################################################
        # Prepares a dropdown list for choosing an icon
        # for a selected device
        try:
            iconArray = []
            iMenu = 'None', 'Default'
            iconArray.append(iMenu)

            # Get icons from PluginPrefs
            for icon in range(1,10):
                iField = 'customIcon'+str(icon)
                iPath = self.pluginPrefs.get(iField,'None')
                if iPath != 'None':
                    iMenu = iPath,'Custom Icon: '+str(icon)
                    iconArray.append(iMenu)
            return iconArray

        except:
            errorHandler('selectIcon')
            return []

    def refreshAllDevices(self, action):

        ################################################
        # Forces a refresh for all devices
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, iDebug5
        try:
            # Causes an automatic refresh of all iDevices
            iUpdate = (int(time.mktime(time.localtime())) - 10)

            for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                if dev.states['deviceActive'] == 'true':
                    dev.updateStateOnServer('timeNextUpdate', value = iUpdate)
                    dev.updateStateOnServer('timeUpdateRead', value=time.asctime(time.localtime(iUpdate)))
                    dev.updateStateOnServer('secondsNextUpdate', value = 0)

            indigo.server.log('Action: All devices refreshed...')
        except:
            errorHandler('refreshAllDevices')

    def refreshDevice(self, action, dev):

        ################################################
        # Forces a refresh for a single device
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5, iDebug5
        try:
            # Causes an automatic refresh of a chosen iDevice
            iUpdate = (int(time.mktime(time.localtime())) - 10)
            if dev.states['deviceActive'] == 'true':
                dev.updateStateOnServer('timeNextUpdate', value = iUpdate)
                dev.updateStateOnServer('timeUpdateRead', value=time.asctime(time.localtime(iUpdate)))
                dev.updateStateOnServer('secondsNextUpdate', value = 0)
            else:
                indigo.server.log("Couldn't refresh device as not active...")

            indigo.server.log('Action: '+dev.name+' will be refreshed...')

        except:
            errorHandler('refreshDevice')

    def refreshMaps(self, action):

        ################################################
        # Forces a refresh for all device maps for control pages
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

        # Refreshes all maps from latest data
        try:
            iRefreshData = self.refreshAllDevices(action)
            iMapStore = self.pluginPrefs.get('mapStorage', '')

            # Get the API key (if it exists)
            mapAPI = self.pluginPrefs.get('mapAPIKey', 'No Key')

            # Update the maps
            iPadMaps = self.pluginPrefs.get('iPadMaps', False)
            iPadMapHorizon = int(self.pluginPrefs.get('iPadMapHorizon', '640'))
            iPadMapVertical=int(self.pluginPrefs.get('iPadMapVertical', '320'))
            iPadMapZoom = int(self.pluginPrefs.get('iPadMapZoom', '15'))
            iPhoneMaps = self.pluginPrefs.get('iPhoneMaps', False)
            iPhoneMapHorizon = int(self.pluginPrefs.get('iPhoneMapHorizon', '320'))
            iPhoneMapVertical=int(self.pluginPrefs.get('iPhoneMapVertical', '160'))
            iPhoneMapZoom = int(self.pluginPrefs.get('iPhoneMapZoom', '15'))

            # Update the maps
            if iPadMaps:
                mapAll = updateAllDeviceMaps(iMapStore, mapAPI, iPadMapHorizon, iPadMapVertical, iPadMapZoom, 'iPad')
                indigo.server.log('iPad Maps refreshed for all devices...')

            if iPhoneMaps:
                mapAll = updateAllDeviceMaps(iMapStore, mapAPI, iPhoneMapHorizon, iPhoneMapVertical, iPhoneMapZoom, 'iPhone')
                indigo.server.log('iPhone Maps refreshed for all devices...')

            if not iPadMaps and not iPhoneMaps:
                indigo.server.log('Map refresh not active for iPad or iPhone')
        except:
            errorHandler('refreshDeviceMaps')

    def refreshOneMap(self, action, dev):

        ################################################
        # Forces a refresh for a device maps for control pages
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:
            # Refreshes map from latest data

            iRefreshData = self.refreshDevice(action, dev)
            iMapStore = self.pluginPrefs.get('mapStorage', '')

            # Get the API key (if it exists)
            mapAPI = self.pluginPrefs.get('mapAPIKey', 'No Key')
            iPadMaps = self.pluginPrefs.get('iPadMaps', False)
            iPadMapHorizon = int(self.pluginPrefs.get('iPadMapHorizon', '640'))
            iPadMapVertical=int(self.pluginPrefs.get('iPadMapVertical', '320'))
            iPadMapZoom = int(self.pluginPrefs.get('iPadMapZoom', '15'))
            iPhoneMaps = self.pluginPrefs.get('iPhoneMaps', False)
            iPhoneMapHorizon = int(self.pluginPrefs.get('iPhoneMapHorizon', '320'))
            iPhoneMapVertical=int(self.pluginPrefs.get('iPhoneMapVertical', '160'))
            iPhoneMapZoom = int(self.pluginPrefs.get('iPhoneMapZoom', '15'))

            # Update the maps
            if iPadMaps:
                mapPad = updateDeviceMap(iMapStore, mapAPI, iPadMapHorizon, iPadMapVertical, iPadMapZoom, dev, "iPad")
                indigo.server.log('iPad Maps refreshed for device:'+dev.name)

            if iPhoneMaps:
                mapPad = updateDeviceMap(iMapStore, mapAPI, iPhoneMapHorizon, iPhoneMapVertical, iPhoneMapZoom, dev, "iPhone")
                indigo.server.log('iPhoneMaps refreshed for device:'+dev.name)

            if not iPadMaps and not iPhoneMaps:
                indigo.server.log('Map refresh not active for iPad or iPhone')
        except:
            errorHandler('refreshOneMap')

    def toggleDeviceAct(self, action, dev):

        ################################################
        # Toggle Active status on a device
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:
            # Causes an automatic refresh of a chosen iDevice
            if dev.states['deviceActive'] == 'true':
                dev.updateStateOnServer('deviceActive', value = 'false')
                iMessage = ' is now Inactive'
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                dev.updateStateOnServer('deviceNearestGeoName', value = "Unknown")
                iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
                if iSingle:
                    iDevFolder = indigo.devices.folders.getId("iFindStuff")
                else:
                    iDevFolder = indigo.devices.folders.getId("iFindStuff Inactive")

                # Move to the Inactive folder
                indigo.device.moveToFolder(dev, value=iDevFolder)

            else:
                dev.updateStateOnServer('deviceActive', value = 'true')
                iMessage = ' is now Active'
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                dev.updateStateOnServer('deviceNearestGeoName', value = "Waiting to update...")
                iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
                if iSingle:
                    iDevFolder = indigo.devices.folders.getId("iFindStuff")
                else:
                    iDevFolder = indigo.devices.folders.getId("iFindStuff Devices")

                # Move to the Inactive folder
                indigo.device.moveToFolder(dev, value=iDevFolder)

                self.refreshDevice('',dev)

            indigo.server.log('Action: '+dev.name+iMessage)
        except:
            errorHandler('toggleDevActive')

    def setDeviceAct(self, action, dev):

        ################################################
        # Toggle Active status on a device
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:
            # Causes an automatic refresh of a chosen iDevice
            dev.updateStateOnServer('deviceActive', value = 'true')
            iMessage = ' is Active'
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
            dev.updateStateOnServer('deviceNearestGeoName', value = "Waiting to update...")
            iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
            if iSingle:
                iDevFolder = indigo.devices.folders.getId("iFindStuff")
            else:
                iDevFolder = indigo.devices.folders.getId("iFindStuff Devices")

            # Move to the active folder
            indigo.device.moveToFolder(dev, value=iDevFolder)

            self.refreshDevice('',dev)
            indigo.server.log('Action: '+dev.name+iMessage)
        except:
            errorHandler('setActive')

    def setDeviceInact(self, action, dev):

        ################################################
        # Toggle Inactive status on a device
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:

            # Causes an automatic refresh of a chosen iDevice
            dev.updateStateOnServer('deviceActive', value = 'false')
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            dev.updateStateOnServer('deviceNearestGeoName', value = "Unknown")

            iMessage = ' is Inactive'

            iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
            if iSingle:
                iDevFolder = indigo.devices.folders.getId("iFindStuff")
            else:
                iDevFolder = indigo.devices.folders.getId("iFindStuff Inactive")

            # Move to the inactive folder
            indigo.device.moveToFolder(dev, value=iDevFolder)

            indigo.server.log('Action: '+dev.name+iMessage)
        except:
            errorHandler('setInActive')

    def refreshFrequencyOn(self, action, dev):
        self.refreshFrequencyExecute(dev, 'ON')

    def refreshFrequencyOff(self, action, dev):
        self.refreshFrequencyExecute(dev, 'OFF')

    def refreshFrequency(self, action, dev):
        self.refreshFrequencyExecute(dev, 'TOGGLE')

    def refreshFrequencyExecute(self, dev, mode):

        ################################################
        # Change between variable and calculated field
        # Mode is
        #   ON - Device Variable used to calculate update
        #   OFF - Device update is calculated
        #   TOGGLE - Switches between states
        #
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:
            # Causes an automatic refresh of a chosen iDevice
            if dev.states['deviceActive'] == 'false':
                # Can't update an inactive device
                indigo.server.log('Action: '+dev.name+' is inactive so action ignored', isError=True)
            else:
                devProps = dev.pluginProps
                iDevName = dev.name
                iDevName=iDevName.replace(" ","")
                iDevName=iDevName.replace("'","")
                iDevName=iDevName.encode('ascii', 'ignore')
                iDevName = iDevName.upper()+'FREQ'

                if 'deviceVariableFrequency' in devProps:
                    if (not devProps['deviceVariableFrequency'] and mode == "TOGGLE") or mode=='ON':
                        devProps['deviceVariableFrequency'] = True
                        iMessage = " is now using "+iDevName+" to control update Frequency"
                        iNow = int(time.mktime(time.localtime()))
                        dev.updateStateOnServer('timeNextUpdate', value = iNow-10)

                        # Update variable being used - does it exist?
                        if not (iDevName in indigo.variables):
                            if not ('iFindStuff' in indigo.variables.folders):
                                # Create the folder
                                iFolderId = indigo.variables.folder.create("iFindStuff")
                                iFolder = iFolderId.id
                            else:
                                iFolder = indigo.variables.folders.getId("iFindStuff")

                            # Need to create and initialise it
                            newVar = indigo.variable.create(iDevName.upper()+'FREQ', "10", iFolder)

                        updateFrequency = int(indigo.variables[iDevName].value)
                        dev.updateStateOnServer('secondsNextUpdate', value = updateFrequency)

                    else:
                        devProps['deviceVariableFrequency'] = False
                        iMessage = " is no longer using "+iDevName+" to control update Frequency and updates will be calculated"

                        # Set the device for a refresh to recalculate the next update schedule time
                        iNow = int(time.mktime(time.localtime()))
                        dev.updateStateOnServer('timeNextUpdate', value = iNow-10)
                        dev.updateStateOnServer('secondsNextUpdate', value = '60')

                elif mode=="TOGGLE" or mode=="OFF":
                    devProps['deviceVariableFrequency'] = False
                    iMessage = " is not using "+iDevName+" to control update Frequency"

                    # Force an update to recalculate the next update scheduled time
                    iNow = int(time.mktime(time.localtime()))
                    dev.updateStateOnServer('timeNextUpdate', value = iNow-10)
                    dev.updateStateOnServer('secondsNextUpdate', value = '60')

                # Update device properties
                dev.replacePluginPropsOnServer(devProps)

            if iDebug3:
                indigo.server.log('Action: '+dev.name+iMessage)
        except:
            errorHandler('refreshFrequencyExecute')

    def toggleGeoAct(self, action, dev):

        ################################################
        # Toggle Active status on a GeoFence
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:
            # Causes an automatic refresh of a chosen iDevice
            geoProps = dev.pluginProps
            if geoProps['geoActive']:
                geoProps['geoActive'] = False
                iMessage = ' is now Inactive'
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                dev.updateStateOnServer('devicesInRange', value = "0")
                dev.updateStateOnServer('devicesNear', value = "0")
                dev.updateStateOnServer('devicesInNestRange', value = "0")
                iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
                if iSingle:
                    iGeoFolder = indigo.devices.folders.getId("iFindStuff")
                else:
                    iGeoFolder = indigo.devices.folders.getId("iFindStuff Inactive")

                # Move to the inactive folder
                indigo.device.moveToFolder(dev, value=iGeoFolder)

            else:
                geoProps['geoActive'] = True
                iMessage = ' is now Active'
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
                if iSingle:
                    iGeoFolder = indigo.devices.folders.getId("iFindStuff")
                else:
                    iGeoFolder = indigo.devices.folders.getId("iFindStuff GeoFences")

                # Move to the inactive folder
                indigo.device.moveToFolder(dev, value=iGeoFolder)

            # Update the server
            dev.replacePluginPropsOnServer(geoProps)
            indigo.server.log('Action: '+dev.name+iMessage)

        except:
            errorHandler('toggleGeoActive')

    def setGeoAct(self, action, dev):

        ################################################
        # Toggle Active status on a GeoFence
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:
            # Causes an automatic refresh of a chosen iDevice
            geoProps = dev.pluginProps
            geoProps['geoActive'] = True
            iMessage = ' is Active'
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
            iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
            if iSingle:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff")
            else:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff GeoFences")

            # Move to the inactive folder
            indigo.device.moveToFolder(dev, value=iGeoFolder)

            # Update the server
            dev.replacePluginPropsOnServer(geoProps)
            indigo.server.log('Action: '+dev.name+iMessage)
        except:
            errorHandler('setGeoActive')

    def setGeoInact(self, action, dev):

        ################################################
        # Toggle Active status on a GeoFence
        # Provided to the user as an iFindStuff Action

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5
        try:
            # Causes an automatic refresh of a chosen iDevice
            geoProps = dev.pluginProps
            geoProps['geoActive'] = False
            iMessage = ' is Inactive'
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            dev.updateStateOnServer('devicesInRange', value = "0")
            dev.updateStateOnServer('devicesNear', value = "0")
            dev.updateStateOnServer('devicesInNestRange', value = "0")
            iSingle=self.pluginPrefs.get('checkboxSingleFolder', False)
            if iSingle:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff")
            else:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff Inactive")

            # Move to the inactive folder
            indigo.device.moveToFolder(dev, value=iGeoFolder)

            # Update the server
            dev.replacePluginPropsOnServer(geoProps)
            indigo.server.log('Action: '+dev.name+iMessage)
        except:
            errorHandler('setGeoInActive')

    def sendMessage(self, action, dev):

        ################################################
        # Allows the user to send a message to a Master Device on
        # a given account.  Doesn't allow messages to linked
        # devices

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

        # Sends a message to an iPhone device
        # First get the phone number for the message
        try:
            iDevice = indigo.devices[dev]
            iUnique = iDevice.states['deviceUniqueKey']
            iAccount = int(iDevice.states['deviceAccount'])
            acc = indigo.devices[iAccount]
            accProps = acc.pluginProps

            # Now get a message
            iUser = accProps['appleId']
            iPass = accProps['applePwd']
            iDeviceMessage = action.props.get("messageContent")
            iDeviceSound = action.props.get("messageSound")
            iLogin = iAuthorise(iUser,iPass)

            if iLogin[0] == 0:
                # Send the message
                api = iLogin[1]
                iAPIDevice = api.devices
                indigo.server.log('Sending message to '+dev.name)
                iAPIDevice[iUnique].display_message(subject='Indigo 6 Message', message=iDeviceMessage, sounds=iDeviceSound)

            return True

        except:
            errorHandler('sendMessage '+dev.name)
            return True

    def getLatLong(self, valuesDict=None, typeId="", dev=0):

        ################################################
        # Opens a web Browser so user can find a latitude and longitude for an address
        # Uses www.latlong.com

        global iDebug1, iDebug2, iDebug3, iDebug4, iDebug5

        try:
            iurl="http://www.latlong.net"
            self.browserOpen(iurl)
        except:
            errorHandler('getLatLong')
            if iDebug1:
                indigo.server.log(u'Default web browser did not open - check Mac set up', isError = True)
                indigo.server.log(u'or issues contacting the www.latlong.net site.  Is internet working?', isError=True)



    def myActiveAccounts(self, filter="", valuesDict=None, typeId="", targetId=0):

        ################################################
        # Provides a list of all Active Devices for dropdown
        # menu selection

        global addAccountId

        try:
            # Is the account locked?
            dev = indigo.devices[targetId]

            if 'accountLocked' in valuesDict:
                if valuesDict['accountLocked']:
                    # This already has an id so it's not new - we're editing so display the account only
                    dev = indigo.devices[targetId]
                    iAccount = int(dev.states['deviceAccount'])
                    iAccountName = dev.states['accountName']
                    iOption = iAccount, iAccountName
                    iDeviceArray = []
                    iDeviceArray.append(iOption)
                    valuesDict['targetAccounts'] = iAccount
                    return iDeviceArray

            # Create an array where each entry is a list - the first item is
            # the value attribute and last is the display string that will be shown
            # Active Devices Only filter
            addAccountId = 0
            gTempKeys = {}
            iDeviceArray = []
            for dev in indigo.devices.iter('self.iAppleAccount'):
                # Only list active devices
                accountProps = dev.pluginProps
                if accountProps['appleActive']:
                    if dev.configured and dev.enabled:
                        # Get Details and store them
                        # Create value & option display
                        iOption = dev.id,dev.name
                        iDeviceArray.append(iOption)

            return iDeviceArray

        except:
            errorHandler('myActiveAccounts')
            return []

    def myAccountDevices(self, filter=0, valuesDict=None, typeId="", targetId=0):

        ################################################
        # Internal - Lists the devices linked to an account that are not assigned

        global addAccountId, gAccountMasterDict

        try:
            # Create an array where each entry is a list - the first item is
            # the value attribute and last is the display string that will be shown
            # Devices filtered on the chosen account

            iDeviceArray = []

            if 'deviceLocked' in valuesDict:
                if valuesDict['deviceLocked']:

                    # We are editing so don't allow changes
                    dev = indigo.devices[targetId]
                    iUnique = dev.states['deviceUniqueKey']
                    iAccountRef = dev.states['deviceAccount']
                    iName = dev.states['deviceName']
                    iOption = iUnique,iName
                    iDeviceArray.append(iOption)
                    valuesDict['targetDevices'] = iUnique
                    return iDeviceArray

            # New device so find devices
            if addAccountId == 0:
                iWait = 0,"Click on account above and select"
                iDeviceArray.append(iWait)
                return iDeviceArray

            # Create a full list of devices
            iDict = createAccountMaster(addAccountId)

            if not iDict[0]:
                # There isn't a map for those devices so return an error
                if iDebug1:
                    indigo.server.log('Failed to find the account:'+str(addAccountId), isError = True)
                return iDeviceArray

            else:
                gAccountMasterDict = iDict[1]
                iAccountRef = str(addAccountId)
                devKeys = gAccountMasterDict[iAccountRef].keys()

                for iKey in devKeys:
                    # Look at each key in turn
                    # First get unique Identifier
                    iUnique = iKey
                    iName =   gAccountMasterDict[iAccountRef][iKey][0]
                    iAssigned = gAccountMasterDict[iAccountRef][iKey][1]

                    if not iAssigned:
                        # Not assigned so can be added to the dropdown
                        # Get Details and store them
                        # Create value & option display
                        iOption = iUnique,iName
                        iDeviceArray.append(iOption)

                return iDeviceArray
        except:
            errorHandler('myActiveAccounts')
            return []

    def selectedAccount(self, valuesDict, typeId, devId):
        global gAccountMasterDict

        ################################################
        # Internal - fixes a selected account and stores the account number
        # to allow device selection

        global addAccountId
        if not 'accountLocked' in valuesDict:
            valuesDict['accountLocked'] = False

        if not valuesDict['accountLocked']:
            addAccountId = int(valuesDict['targetAccounts'])
            valuesDict['accountLocked'] = True
            return valuesDict
        else:
            dev = indigo.devices[devId]
            addAccountId = int(valuesDict['targetAccounts'])
            valuesDict['targetDevices'] = dev.states['deviceUniqueKey']
            return valuesDict

    def selectedDevice(self, valuesDict, typeId, devId):

        ################################################
        # Internal - fixes a selected device and stores the device number
        # before allowing access to other customisation options
        global gAccountMasterDict

        # Selected device now take other actions
        if not 'deviceLocked' in valuesDict:
            valuesDict['deviceLocked'] = False

        if not valuesDict['deviceLocked']:
            dev = indigo.devices[devId]
            acc = indigo.devices[addAccountId]
            iDevName = gAccountMasterDict[str(addAccountId)][valuesDict['targetDevices']][0]
            dev.updateStateOnServer('deviceName',value=iDevName)
            dev.updateStateOnServer('deviceAccount', value=str(acc.id))
            dev.updateStateOnServer('accountName', value=str(acc.name))
            dev.updateStateOnServer('deviceUniqueKey', value=valuesDict['targetDevices'])
            valuesDict['frequencyTimer'] = self.pluginPrefs.get('refreshTime','600')
            valuesDict['frequency50'] = self.pluginPrefs.get('refreshTime50','1000')
            valuesDict['frequency40'] = self.pluginPrefs.get('refreshTime40','1500')
            valuesDict['frequency30'] = self.pluginPrefs.get('refreshTime30','3600')
            valuesDict['stationaryMode'] = False
            valuesDict['distanceStation'] = self.pluginPrefs.get('stationaryDefault','50')
            valuesDict['deviceLocked'] = True
            valuesDict['targetDevices'] = dev.states['deviceUniqueKey']
        else:
            dev = indigo.devices[devId]
            valuesDict['targetDevices'] = dev.states['deviceUniqueKey']

        return valuesDict


    ########################################
    # Actions defined in MenuItems.xml. These are options that can be accessed via the iFindStuff Menu option
    ####################
    def createGeoFence(self,valuesDict, typeId):

        ################################################
        # Creates a geofence from the coordinates of a device

        try:
            # Choose a device as a reference
            iGeoDevice = int(valuesDict[u"devTarget"])
            dev = indigo.devices[iGeoDevice]

            # Device selected?
            if dev.id == 0:
                return valuesDict
        except:
            errorHandler('createGeoFence '+dev.name)
            if iDebug1:
                indigo.server.log(u'Issues with selecting devices for plotting - probable code error - '
                                  u'advise Developer - GC')

        # Now get the device information
        try:
            iLatDevice = dev.states['deviceLatitude']
            iLongDevice = dev.states['deviceLongitude']
            iDeviceType = 'iGeoFence'
            iGeoName = valuesDict['geoCreateName']
            iGeoRange = valuesDict['geoRangeNeeded']
            iGeoDesc = 'GeoFence automatically created from device:'+dev.name
            geoDict = {

                'geoName': iGeoName,
                'geoDescription': iGeoDesc,
                'geoLatitude': iLatDevice,
                'geoLongitude': iLongDevice,
                'geoHome': False,
                'geoActive': True,
                'geoNEST': False,
                'geoPower' :False,
                'geoPowerTime': u'900',
                'geoRange': iGeoRange
            }

            # Now create the Geo
            # Get the Folder ids
            iSingle = self.pluginPrefs.get('checkboxSingleFolder', False)

            if iSingle:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff")
            else:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff GeoFences")

            # Now create
            newGeoDevice = indigo.device.create(protocol=indigo.kProtocol.Plugin, deviceTypeId=iDeviceType,
                                                 name=iGeoName,
                                                 description=iGeoDesc, folder=iGeoFolder, props=geoDict)
            newGeoDevice.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
            indigo.device.displayInRemoteUI(newGeoDevice, value=True)
            indigo.device.enable(newGeoDevice, value=True)
            iPlace = iGeoLocation()

        except:
            errorHandler('createGeoFence')

        return True, valuesDict

    def toggleGeoActive(self, valuesDict, typeId):

        ################################################
        # Allows the toggling of active flag on a GeoFence
        # and moves devices between Active and Not Active Folders

        iTracking = self.pluginPrefs.get('checkboxTrack', False)
        iSingle = self.pluginPrefs.get('checkboxSingleFolder', False)

        try:
            # Get the Folder ids
            if iSingle:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff")
                iInFolder = indigo.devices.folders.getId("iFindStuff")
            else:
                iGeoFolder = indigo.devices.folders.getId("iFindStuff GeoFences")
                iInFolder = indigo.devices.folders.getId("iFindStuff Inactive")
        except:
            errorHandler('toggleGeoActive ')
            if iDebug1:
                indigo.server.log(u'Failed to get the folder ids - coding issue - advise Developer')
        try:
            # Choose a device for toggle
            iDeviceToggle = int(valuesDict[u"targetGeo"])
            dev = indigo.devices[iDeviceToggle]
            geoProps = dev.pluginProps

        except:
            errorHandler('toggleGeoActive ')
            if iDebug1:
                indigo.server.log(u'Failed to access geofence list - probable error in Devices.xml')

        # Device selected?
        if iDeviceToggle == 0:
            return True, valuesDict

        try:
            iDeviceActive = valuesDict[u'activeGeo']
            if iDeviceActive != geoProps['geoActive']:
                if iDeviceActive:
                    # If active - move to the iFindStuff Folder
                    indigo.device.moveToFolder(dev, value=iGeoFolder)
                    geoProps['geoActive'] = True
                    dev.replacePluginPropsOnServer(geoProps)
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                else:
                    # if inactive - move to the iFindStuff Folder
                    indigo.device.moveToFolder(dev, value=iInFolder)
                    geoProps['geoActive'] = False
                    dev.replacePluginPropsOnServer(geoProps)
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            else:
                if iDebug2:
                    indigo.server.log(u'Device state not changed so no changes in geofence location')
                return True, valuesDict

        except:
            errorHandler('toggleGeoActive ')
            if iDebug1:
                indigo.server.log(u'Failed to update device icon - coding error - advise Developer')

        # Now recheck the Geolocations for each device
        iGeoLocation(iTracking)

        return True, valuesDict

    def messageDevice(self, valuesDict, typeId):

        ################################################
        # Allows the user to send a message from the Menu
        # Options

        global debug

        # Sends a message to an iPhone device
        # First get the phone number for the message
        try:
            iDeviceToggle = int(valuesDict[u"targetMessage"])
            dev = indigo.devices[iDeviceToggle]
            iUnique = dev.states['deviceUniqueKey']
            iAccount = int(dev.states['deviceAccount'])
            acc = indigo.devices[iAccount]
            accProps = acc.pluginProps

            # Now get a message
            iDeviceMessage = valuesDict[u'messageDevice']
            iDeviceSound = valuesDict[u'soundDevice']
            iUser = accProps['appleId']
            iPass = accProps['applePwd']

            iLogin = iAuthorise(iUser,iPass)

            if iLogin[0] == 0:
                # Send the message
                api = iLogin[1]
                iAPIDevice = api.devices
                indigo.server.log('Sending message to '+dev.name)
                iAPIDevice[iUnique].display_message(subject='Indigo 6 Message', message=iDeviceMessage, sounds=iDeviceSound)

            return True

        except:
            errorHandler('messageDevice '+dev.name)

            if iDebug2:
                indigo.server.log('Failed to send message - reason unknown - contact Developer')
            return True

    def toggleDeviceActive(self, valuesDict, typeId):

        ################################################
        # Allows the toggling of active flag on a device
        # and moves devices between Active and Not Active Folders
        iTracking = self.pluginPrefs.get('checkboxTrack', False)
        iSingle = self.pluginPrefs.get('checkboxSingleFolder', False)

        try:
            if iSingle:
                # Get the Folder ids
                iDevFolder = indigo.devices.folders.getId("iFindStuff")
                iInFolder = indigo.devices.folders.getId("iFindStuff")
            else:
                # Get the Folder ids
                iDevFolder = indigo.devices.folders.getId("iFindStuff Devices")
                iInFolder = indigo.devices.folders.getId("iFindStuff Inactive")
        except:
            errorHandler('toggleDeviceActive ')
            if iDebug1:
                indigo.server.log(u'Failed to get the folder ids - coding issue - advise Developer')
        try:
            # Choose a device for toggle
            iDeviceToggle = int(valuesDict[u"targetToggle"])
            dev = indigo.devices[iDeviceToggle]

        except:
            errorHandler('toggleDeviceActive '+dev.name)
            if iDebug1:
                indigo.server.log(u'Failed to access device list - probable error in Devices.xml')

        # Device selected?
        if iDeviceToggle == 0:
            return True, valuesDict

        try:
            iDeviceActive = valuesDict[u'activeDevice']
            if iDeviceActive != dev.states['deviceActive']:
                if iDeviceActive:
                    # If active - move to the iFindStuff Folder
                    indigo.device.moveToFolder(dev, value=iDevFolder)
                    dev.updateStateOnServer('deviceActive', value='true')
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                else:
                    # if inactive - move to the iFindStuff Folder
                    indigo.device.moveToFolder(dev, value=iInFolder)
                    dev.updateStateOnServer('deviceActive', value='false')
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            else:
                if iDebug3:
                    indigo.server.log(u'Device state not changed so no changes in device location')
                    return True, valuesDict
        except:
            errorHandler('toggleDeviceActive ')
            if iDebug1:
                indigo.server.log(u'Failed to update device icon - coding error - advise Developer')

        # Now update the GeoLocation range & near numbers
        iGeoLocation(iTracking)

        return True, valuesDict

    def createHomeGeo(self):

        ################################################
        # Allows the user to create a Home Geofence if one
        # doesn't exist.  User can also convert any GeoFence to
        # a Home Geofence.  This is a legacy option

        try:
            # Create a Home GeoFence
            indigo.server.log(u'Creating Home GeoFence...')

            # Does it exist already?
            if 'Home GeoFence' in indigo.devices:
                # Already there
                if iDebug2:
                    indigo.server.log('** Home GeoFence already created **')

            else:
                try:
                    iDeviceType = 'iGeoFence'
                    iName ='Home GeoFence'
                    iDesc = 'Home location based on Indigo Server Latitude and Longitude'
                    if not ('iFindStuff GeoFences' in indigo.devices.folders):
                        # Create the folder
                        iFolderId = indigo.devices.folder.create("iFindStuff GeoFences")
                        iFolder = iFolderId.id
                    else:
                        iFolder = indigo.devices.folders.getId("iFindStuff GeoFences")

                    iNewDevice = indigo.device.create(protocol=indigo.kProtocol.Plugin, deviceTypeId=iDeviceType,
                                                         name=iName,
                                                         description=iDesc, folder=iFolder)
                except:
                    errorHandler('createHomeGeo ')
                    if iDebug1:
                        indigo.server.log(u'Failed to create Home GeoFence - '
                                          u'create manually as workaround & advise developer')
                try:
                    # Now sync the device states on the server
                    latLong=indigo.server.getLatitudeAndLongitude()
                    lat = latLong[0]
                    long = latLong[1]
                    localProps = iNewDevice.pluginProps

                    localProps['geoName'] ='Home GeoFence'
                    localProps['geoDescription']='Home GeoFence based on the latitude and longitude of the Indigo Server'
                    localProps['geoLatitude']=lat
                    localProps['geoLongitude']=long
                    localProps['geoRange']="100"
                    localProps['geoActive']='true'
                    localProps['geoNEST']='false'
                    iNewDevice.replacePluginPropsOnServer(localProps)
                    iNewDevice.updateStateOnServer('devicesNear', value="0")
                    iNewDevice.updateStateOnServer('devicesInRange', value="0")
                    iNewDevice.updateStateOnServer('devicesInNestRange', value="0")
                    iNewDevice.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    # Enable the device
                    indigo.device.displayInRemoteUI(iNewDevice, value=True)
                    indigo.device.enable(iNewDevice, value=True)

                except:
                    errorHandler('createHomeGeo ')
                    if iDebug1:
                        indigo.server.log('Failed to update states on New Home GeoFence - '
                                          'edit and update & advise Developer')
        except:
            errorHandler('createHomeGeo ')
            if iDebug1:
                indigo.server.log(u'General failure to create Home GeoFence - create manually & advise Developer')

    def myDevices(self, filter="", valuesDict=None, typeId="", targetId=0):

        ################################################
        # Lists all devices (regardless of status)

        try:
            # Create an array where each entry is a list - the first item is
            # the value attribute and last is the display string that will be shown
            # All Devices
            iDeviceArray = []
            for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                # Only list active devices
                if dev.configured and dev.enabled:
                    # Get Details and store them
                    # Create value & option display
                    iOption = dev.id,dev.name
                    iDeviceArray.append(iOption)

            return iDeviceArray

        except:
            errorHandler('myDevices ')
            if iDebug1:
                indigo.server.log(u'Failed to create a list of all devices - advise Developer')

    def myActiveDevices(self, filter="", valuesDict=None, typeId="", targetId=0):

        ################################################
        # Lists all active devices (regardless of status)

        try:
            # Create an array where each entry is a list - the first item is
            # the value attribute and last is the display string that will be shown
            # Active Devices Only filter

            iDeviceArray = []
            for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                # Only list active devices
                if dev.states['deviceActive'] == 'true':
                    if dev.configured and dev.enabled:
                        # Get Details and store them
                        # Create value & option display
                        iOption = dev.id,dev.name
                        iDeviceArray.append(iOption)

            return iDeviceArray

        except:
            errorHandler('myActiveDevices ')
            if iDebug1:
                indigo.server.log(u'Failed to create a list of active devices - advise Developer')

    def myGeos(self, filter="", valuesDict=None, typeId="", targetId=0):

        ################################################
        # Lists all geos (regardless of status)

        try:
            # Create an array where each entry is a list - the first item is
            # the value attribute and last is the display string that will be shown
            # All devices
            iDeviceArray = []
            for dev in indigo.devices.iter('self.iGeoFence'):
                geoProps = dev.pluginProps
                if dev.configured and dev.enabled:
                    # Get Details and store them
                    # Create value & option display
                    iOption = dev.id, dev.name
                    iDeviceArray.append(iOption)

            return iDeviceArray

        except:
            errorHandler('myGeos ')
            if iDebug1:
                indigo.server.log(u'Failed to create a list of all geofences - advise Developer')

    def myActiveGeos(self, filter="", valuesDict=None, typeId="", targetId=0):

        ################################################
        # Lists active geos (regardless of status)

        try:
            # Create an array where each entry is a list - the first item is
            # the value attribute and last is the display string that will be shown
            # Only Active GeoFences filter
            iDeviceArray = []
            for dev in indigo.devices.iter('self.iGeoFence'):
                geoProps = dev.pluginProps
                if geoProps['geoActive']:
                    if dev.configured and dev.enabled:
                        # Get Details and store them
                        # Create value & option display
                        iOption = dev.id, dev.name
                        iDeviceArray.append(iOption)

            return iDeviceArray

        except:
            errorHandler('myActiveGeos ')
            if iDebug1:
                indigo.server.log(u'Failed to create a list of active geofences - advise Developer')

    def displayDevices(self, valuesDict, typeId):

        ################################################
        # Generates a Dynamic Google Map for a single device

        try:
            # Set up map files
            iCustom = True
            iMapFiles = self.pluginPrefs.get('mapStorage','/Library/Application Support/Perceptive Automation/Indigo 6/Plugins/iFindStuff.indigoPlugin/Contents/Server Plugin/pygmaps')
            if len(iMapFiles) == 0:
                # Set to default
                iCustom = False
                iMapFiles = '/Library/Application Support/Perceptive Automation/Indigo 6/Plugins/iFindStuff.indigoPlugin/Contents/Server Plugin/pygmaps'

        except:
            errorHandler('displayDevices ')
            if iDebug1:
                indigo.server.log(u'Failed to find directory for maps - '
                                   u'check the spelling of the plugin file in Indigo/Plugins - 1D')
                return
        try:
            # Now choose a device for plotting
            iDevicePlot = int(valuesDict[u"targetDevices"])
            dev = indigo.devices[iDevicePlot]
            iShowHistory = valuesDict['plotHistory']
            iHistory = 3600*24 # One Day of History only
            iTimeCheck = time.time()-float(iHistory)

            if iCustom:
                iPrefix = dev.name
                iPrefix = iPrefix.encode('ascii', 'ignore')
                iPrefix = iPrefix.replace("'","")
            else:
                iPrefix = ''

            # Device selected?
            if iDevicePlot == 0:
                return True, valuesDict

        except:
            errorHandler('displayDevices')
            if iDebug1:
                indigo.server.log(u'Issues with selecting devices for plotting - probable code error - '
                                  u'advise Developer - 1D')

        try:
            # Now plot the device and all geofences
            devProps = dev.pluginProps
            if 'customMap' in devProps:
                    iCustomIcon = devProps['customMap']
            else:
                iCustomIcon = ''

            if iCustomIcon == 'None' or len(iCustomIcon) == 0:
                # Use standard icon
                iCustomIcon = 'smartphone.png'

            iLatDevice = float(dev.states['deviceLatitude'])
            iLongDevice = float(dev.states['deviceLongitude'])
            iDevName =  dev.states['deviceName'].encode(''
                                                        'ascii', 'ignore')
            iDevType = 'device'
            iColourDev = "00FFFF"

            # Create the map with the device in the centre
            mymap = maps(iLatDevice, iLongDevice, 16)

            # Now add the geofences first
            iCustomGeo = self.pluginPrefs.get('customGeoFence', 'homemarker.png')
            if iCustomGeo == 'None' or len(iCustomIcon) == 0:
            # Use standard icon
                iCustomGeo = 'homemarker.png'

            for geo in indigo.devices.iter('self.iGeoFence'):
                localProps = geo.pluginProps
                gLat = float(localProps['geoLatitude'])
                gLon = float(localProps['geoLongitude'])
                gRange = int(localProps['geoRange'])

                # May need to correct the georange to the current units (ft to metres)
                if gUnits == 'Imperial':
                    # Range is in ft so convert
                    gRange = int(float(gRange) * 0.3048)

                if localProps['geoHome']:
                    gColourRad = "FF00FF"
                    gColourGFC = "FF0000"
                    gType = 'geofence'
                else:
                    gColourRad = "0000FF"
                    gColourGFC = "FF0000"
                    gType = 'geofence'

                gColourDev = "00FFFF"
                geoName = localProps['geoName']

                # Add the geopoint and radius
                mymap.addradpoint(gLat, gLon, gRange, gColourRad)
                mymap.addpoint(gLat, gLon, gColourRad, geoName, gType, iCustomGeo)

            # Now the target
            mymap.addpoint(iLatDevice, iLongDevice, iColourDev, iDevName, iDevType, iCustomIcon)

            # Now the plot for the target if required
            if iShowHistory:

                # Analyse the current database
                if iTrackHistory:
                    # We are tracking history so there should be some data
                    plotData = db.search((where ('name') == dev.name) & (where ('timestamp') >= iTimeCheck))
                    if len(plotData) > 0:
                        # Data to plot
                        myplot = []
                        for plots in range(len(plotData)):
                            myTuple = float(plotData[plots]['lat']), float(plotData[plots]['lon'])
                            myplot.append(myTuple)

                        # Add the history to the map
                        mymap.addpath(myplot,color='#FF0000')

                    else:
                        indigo.server.log('** No tracking data to plot **')
                else:
                    indigo.server.log('** Device tracking not enabled in configuration **')


        except:
            errorHandler('displayDevices')
            if iDebug1:
                indigo.server.log(u'Issues with mymap.py - advise Developer - 1D')

        try:
            # Prepare the file and draw the map
            iFileName = iMapFiles+'/mymap'+iPrefix.upper()+'.html'
            mymap.draw(iFileName)
            url = iFileName
            indigo.server.log('Opening Map...'+iFileName)
            webbrowser.open(url)

        except:
            errorHandler('displayDevices')

        return True, valuesDict

    def displayAllDevices(self):

        ################################################
        # Generates a Dynamic Google Map for all devices

        # Set up map files
        iCustom = True
        iMapFiles = self.pluginPrefs.get('mapStorage','/Library/Application Support/Perceptive Automation/Indigo 6/Plugins/iFindStuff.indigoPlugin/Contents/Server Plugin/pygmaps')
        if len(iMapFiles) == 0:
            # Set to default
            iCustom = False
            iMapFiles = '/Library/Application Support/Perceptive Automation/Indigo 6/Plugins/iFindStuff.indigoPlugin/Contents/Server Plugin/pygmaps'

        # Add prefix
        iPrefix = 'ALL DEVICES'

        # Now plot the device and all geofences
        # Flag map plotted
        iMap = False

        for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
            try:
                if len(dev.states['deviceLatitude']) == 0 or len(dev.states['deviceLongitude']) == 0:
                    # No position so ignore
                    continue

                if dev.states['deviceActive'] == 'false':
                    # Device is inactive so ignore
                    continue

                devProps = dev.pluginProps
                if 'customMap' in devProps:
                    iCustomIcon = devProps['customMap']
                else:
                    iCustomIcon = ''

                if iCustomIcon == 'None' or len(iCustomIcon) == 0:
                    # Use standard icon
                    iCustomIcon = 'smartphone.png'

                # Get position details from the geo device
                iLatDevice = float(dev.states['deviceLatitude'])
                iLongDevice = float(dev.states['deviceLongitude'])
                iDevName =  dev.states['deviceName'].encode('ascii', 'ignore')
                iDevType = 'device'
                iColourDev = "00FFFF"

                if iLatDevice == 0 or iLongDevice == 0:
                    # Invalid position so continue to next
                    continue

                # Create the map with the device in the centre if not already done
                if not iMap:
                    iMap = True
                    # Centre on the Master Phone
                    mymap = maps(iLatDevice, iLongDevice, 13)

                # Set Device Colour
                gColourDev = "FFFF00"

                # Plot the device
                mymap.addpoint(iLatDevice, iLongDevice,iColourDev,iDevName,iDevType,iCustomIcon)

                # Now add the geofences icon
                iCustomGeo = self.pluginPrefs.get('customGeoFence', 'homemarker.png')
                if iCustomGeo == 'None' or len(iCustomIcon) == 0:
                # Use standard icon
                    iCustomGeo = 'homemarker.png'

                # Now add the geofences
                for geo in indigo.devices.iter('self.iGeoFence'):
                    localProps = geo.pluginProps

                    if not localProps['geoActive']:
                        # Geopoint is inactive so ignore
                        continue

                    gLat = float(localProps['geoLatitude'])
                    gLon = float(localProps['geoLongitude'])
                    gRange = int(localProps['geoRange'])
                    gName = localProps['geoName']
                    if localProps['geoHome']:
                        gColourRad = "FF00FF"
                        gColourGFC = "FF0000"
                        gType = 'geofence'
                    else:
                        gColourRad = "0000FF"
                        gColourGFC = "FF0000"
                        gType = 'geofence'

                    if gUnits == 'Imperial':
                        # Range is in ft so convert
                        gRange = int(float(gRange) * 0.3048)

                    # Add the geopoint and radius
                    mymap.addradpoint(gLat, gLon, gRange, gColourRad)
                    mymap.addpoint(gLat, gLon,gColourGFC,gName, gType, iCustomGeo)

            except:
                errorHandler('displayAllDevices')
                if iDebug1:
                    indigo.server.log(u'Issues with mymap.py - advise Developer - AD')

        try:
            # Prepare the file and draw the map
            iFileName = iMapFiles+'/mymap'+iPrefix.upper()+'.html'
            mymap.draw(iFileName)
            url = iFileName
            indigo.server.log('Opening Map...'+iFileName)
            webbrowser.open(url)

        except:
            errorHandler('displayAllDevices ')
            if iDebug1:
                indigo.server.log(u'Issues with opening map in default browswer - advise Developer - AD')

            return True

    def iPrint(self, valuesDict, typeId):
        ################################################
        # Generates a report of all information provided
        # by the user
        global db, iTrackHistory

        try:
            # Header
            indigo.server.log('\n\n')
            indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')
            indigo.server.log('iFindStuff Devices report')
            indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')

            # Devices information
            # Get summary information
            # Active devices
            devActive = 0
            devInActive = 0
            indigo.server.log('Active Devices')
            indigo.server.log('--------------')
            for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                if not valuesDict['allDevices']:
                    if dev.id != int(valuesDict['targetReport']):
                        continue

                if dev.states['deviceActive'] == 'true':
                    devActive = devActive + 1
                    indigo.server.log(''+ dev.name.upper()+' : '+str(dev.states['deviceBattery']))
                    indigo.server.log('Latitude:'+str(dev.states['deviceLatitude'])+' Longitude:'+str(dev.states['deviceLongitude']))
                    indigo.server.log('Google address:'+str(dev.states['deviceAddress']))
                    indigo.server.log('Nearest GeoFence:'+str(dev.states['deviceNearestGeoName'])+' '+str(dev.states['geoDistanceDisplay']))
                    indigo.server.log('Home GeoFence:'+str(dev.states['geoHomeName'])+' '+str(dev.states['geoHomeDistanceDisplay']))
                    indigo.server.log('Real Distance Home:'+str(dev.states['realDistanceHome'])+' Travel Time:'+str(dev.states['realTimeHome']))
                    indigo.server.log('Last checked:'+str(dev.states['deviceTimeChecked'])+' Next Check:'+str(dev.states['timeUpdateRead']))
                    indigo.server.log('Update Frequency:'+str(dev.states['secondsNextUpdate']))
                    indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')

                    if valuesDict['includeTracking']:
                        try:
                            # User has requested tracking
                            # Check tracking history is on
                            if iTrackHistory:
                                # Generate a report for the device
                                iDeviceHistory = db.search(where ('name') == dev.name)

                                # Get the number of days requested from now to calculate early cut off time
                                iDays = valuesDict['includeRange']
                                iDayCheck = time.time() - int(iDays)*3600*24 # convert to seconds

                                if len(iDeviceHistory) > 0:
                                    # Some records to report on
                                    # Print Headings
                                    Head1 = 'Time'.ljust(20)[:20]
                                    Head2 = 'Address'.ljust(40)[:40]
                                    Head3 = 'Nearest Geo'.ljust(20)[:20]
                                    Head4 = 'In Range'.ljust(10)[:10]
                                    Head5 = 'Home Geo'.ljust(20)[:20]
                                    Head6 = 'Distance'.ljust(20)[:20]
                                    Head7 = 'Latitude'.ljust(10)[:10]+'  '
                                    Head8 = 'Longitude'.ljust(10)[:10]
                                    indigo.server.log(Head1+Head2+Head3+Head4+Head5+Head6+Head7+Head8)
                                    for j in range(len(iDeviceHistory)):
                                        if iDeviceHistory[j]['timestamp']>=iDayCheck:
                                            # in Day Range - defaults to 1
                                            Col1 = time.asctime(time.localtime(iDeviceHistory[j]['timestamp'])).ljust(20)[:20]
                                            Col2 = iDeviceHistory[j]['add'].ljust(38)[:38]+'  '
                                            Col3 = iDeviceHistory[j]['geoName'].ljust(20)[:20]
                                            if iDeviceHistory[j]['geoRange'] == 'true':
                                                geoInRange = 'Yes'
                                            else:
                                                geoInRange = 'No'
                                            Col4 = geoInRange.ljust(10)[:10]
                                            Col5 = iDeviceHistory[j]['geoHome'].ljust(20)[:20]
                                            Col6 = iDeviceHistory[j]['homeDist'].ljust(20)[:20]
                                            Col7 = iDeviceHistory[j]['lat'].ljust(10)[:10]+'  '
                                            Col8 = iDeviceHistory[j]['lon'].ljust(10)[:10]
                                            indigo.server.log(Col1+Col2+Col3+Col4+Col5+Col6+Col7+Col8)
                                else:
                                    indigo.server.log('** No tracking data to report for this device **')
                                # Print a separator
                                indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')
                            else:
                                indigo.server.log('** Tracking is not enabled in Configuration **')

                            # Print a separator
                            indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')

                        except:
                            errorHandler('iPrint - tracking issue')

            if valuesDict['allDevices']:
                indigo.server.log('iFindStuff Active Devices on database:'+str(devActive))
                indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')

            if valuesDict['includeInactives']:
                indigo.server.log('Inactive Devices')
                indigo.server.log('--------------')
                for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                    if dev.states['deviceActive'] == 'false':
                        devInActive = devInActive + 1
                        indigo.server.log(''+ dev.name.upper())
                        indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')

                indigo.server.log('iFindStuff Inactive Devices on database:'+str(devInActive))
                indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')

            # GeoFence information
            # Get summary information
            # Active Geos
            if valuesDict['includeGeos']:
                indigo.server.log('Active GeoFences')
                indigo.server.log('----------------')
                geoActiveCount = 0
                geoInActiveCount = 0
                for geo in indigo.devices.iter('self.iGeoFence'):

                    geoProps = geo.pluginProps
                    if geoProps['geoActive']:
                        geoActiveCount = geoActiveCount + 1
                        indigo.server.log(''+ geo.name.upper())
                        indigo.server.log('Latitude:'+str(geoProps['geoLatitude'])+' Longitude:'+str(geoProps['geoLongitude']))
                        useUnits = displayUnits()
                        indigo.server.log('Range:'+str(geoProps['geoRange'])+str(useUnits[1]))
                        indigo.server.log('Home GeoFence:'+str(geoProps['geoHome'])+' Nest GeoFence:'+str(geoProps['geoNEST'])+' '+'Power Saving Geofence:'+str(geoProps['geoPower']))
                        indigo.server.log('Devices near:'+str(int(geo.states['devicesNear']))+' Devices in range:'+str(int(geo.states['devicesInRange']))+' Nest Devices in range:'+str(int(geo.states['devicesInNestRange'])))
                        devFoundInGeo = 0

                        for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                            # Devices in the GeoFence
                            if dev.states['deviceNearestGeoName'].upper() == geoProps['geoName'].upper():
                                devFoundInGeo = devFoundInGeo + 1
                                indigo.server.log('\t'+dev.name.upper())

                        if geoActiveCount == 0:
                            indigo.server.log('** NONE **')

                        indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')

                indigo.server.log('iFindStuff Active GeoFences on database:'+str(geoActiveCount))
                indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')

                # Inactive GeoFences
                if valuesDict['includeInactives']:
                    indigo.server.log('Inactive GeoFences')
                    indigo.server.log('------------------')
                    for geo in indigo.devices.iter('self.iGeoFence'):
                        geoProps = geo.pluginProps
                        if not geoProps['geoActive']:
                            geoInActiveCount = geoInActiveCount + 1
                            indigo.server.log(''+ geo.name.upper())
                            indigo.server.log('Latitude:'+str(geoProps['geoLatitude'])+' Longitude:'+str(geoProps['geoLongitude']))
                            useUnits = displayUnits()
                            indigo.server.log('Range:'+str(geoProps['geoRange'])+str(useUnits[1]))
                            indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------')

                    indigo.server.log('iFindStuff Inactive GeoFences on database:'+str(geoInActiveCount))
                    indigo.server.log('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
                return True

        except:
            errorHandler('iPrint')

        return True

    def iSavePrint(self, valuesDict, typeId):
        ################################################
        # Generates a report of all information provided
        # by the user and saves it to the MAPS directory

        # Get Maps Directory and open a file
        try:
            indigo.server.log('Generating report...')
            iMapStore = self.pluginPrefs.get('mapStorage', '').upper()
            iFileName = 'FindStuff Report '+str(time.localtime()[2])+'-'+str(time.localtime()[1])+'-'+str(time.localtime()[0])+'_'+str(time.localtime()[3])+'-'+str(time.localtime()[4])+'-'+str(time.localtime()[5])+'.txt'
            iFileName = iMapStore+'/'+iFileName.upper()
            f = open(iFileName, 'w')

            # Header
            f.write('\n\n')
            f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
            f.write('iFindStuff Devices report\n')
            f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')

            # Devices information
            # Get summary information
            # Active devices
            devActive = 0
            devInActive = 0
            f.write('Active Devices\n')
            f.write('--------------\n')
            for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                if not valuesDict['allSaveDevices']:
                    if dev.id != int(valuesDict['targetSave']):
                        continue

                if dev.states['deviceActive'] == 'true':
                    devActive = devActive + 1
                    f.write(''+ dev.name.upper()+' : '+str(dev.states['deviceBattery'])+'\n')
                    f.write('Latitude:'+str(dev.states['deviceLatitude'])+' Longitude:'+str(dev.states['deviceLongitude'])+'\n')
                    f.write('Google address:'+str(dev.states['deviceAddress'])+'\n')
                    f.write('Nearest GeoFence:'+str(dev.states['deviceNearestGeoName'])+' '+str(dev.states['geoDistanceDisplay'])+'\n')
                    f.write('Home GeoFence:'+str(dev.states['geoHomeName'])+' '+str(dev.states['geoHomeDistanceDisplay'])+'\n')
                    f.write('Real Distance Home:'+str(dev.states['realDistanceHome'])+' Travel Time:'+str(dev.states['realTimeHome'])+'\n')
                    f.write('Last checked:'+str(dev.states['deviceTimeChecked'])+' Next Check:'+str(dev.states['timeUpdateRead'])+'\n')
                    f.write('Update Frequency:'+str(dev.states['secondsNextUpdate'])+'\n')
                    f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------'+'\n')

                    if valuesDict['includeSaveTrack']:
                        try:
                            # User has requested tracking
                            # Check tracking history is on
                            if iTrackHistory:
                                # Generate a report for the device
                                iDeviceHistory = db.search(where ('name') == dev.name)

                                # Get the number of days requested from now to calculate early cut off time
                                iDays = valuesDict['includeSaveRange']
                                iDayCheck = time.time() - int(iDays)*3600*24 # convert to seconds

                                if len(iDeviceHistory) > 0:
                                    # Some records to report on
                                    # Print Headings
                                    Head1 = 'Time'.ljust(20)[:20]
                                    Head2 = 'Address'.ljust(40)[:40]
                                    Head3 = 'Nearest Geo'.ljust(20)[:20]
                                    Head4 = 'In Range'.ljust(10)[:10]
                                    Head5 = 'Home Geo'.ljust(20)[:20]
                                    Head6 = 'Distance'.ljust(20)[:20]
                                    Head7 = 'Latitude'.ljust(10)[:10]+'  '
                                    Head8 = 'Longitude'.ljust(10)[:10]
                                    f.write(Head1+Head2+Head3+Head4+Head5+Head6+Head7+Head8+'\n')
                                    for j in range(len(iDeviceHistory)):
                                        if iDeviceHistory[j]['timestamp']>=iDayCheck:
                                            # in Day Range - defaults to 1
                                            Col1 = time.asctime(time.localtime(iDeviceHistory[j]['timestamp'])).ljust(20)[:20]
                                            Col2 = iDeviceHistory[j]['add'].ljust(38)[:38]+'  '
                                            Col3 = iDeviceHistory[j]['geoName'].ljust(20)[:20]
                                            if iDeviceHistory[j]['geoRange'] == 'true':
                                                geoInRange = 'Yes'
                                            else:
                                                geoInRange = 'No'
                                            Col4 = geoInRange.ljust(10)[:10]
                                            Col5 = iDeviceHistory[j]['geoHome'].ljust(20)[:20]
                                            Col6 = iDeviceHistory[j]['homeDist'].ljust(20)[:20]
                                            Col7 = iDeviceHistory[j]['lat'].ljust(10)[:10]+'  '
                                            Col8 = iDeviceHistory[j]['lon'].ljust(10)[:10]
                                            f.write(Col1+Col2+Col3+Col4+Col5+Col6+Col7+Col8+'\n')
                                else:
                                    f.write('** No tracking data to report for this device **'+'\n')
                                # Print a separator
                                f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------'+'\n')
                            else:
                                f.write('** Tracking is not enabled in Configuration **'+'\n')

                            # Print a separator
                            f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------'+'\n')

                        except:
                            errorHandler('iSave - tracking issue')

            if valuesDict['allSaveDevices']:
                f.write('iFindStuff Active Devices on database:'+str(devActive)+'\n')
                f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n'+'\n')

            if valuesDict['includeSaveInactives']:
                f.write('Inactive Devices'+'\n')
                f.write('--------------'+'\n')
                for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                    if dev.states['deviceActive'] == 'false':
                        devInActive = devInActive + 1
                        f.write(''+ dev.name.upper()+'\n')
                        f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------'+'\n')

                f.write('iFindStuff Inactive Devices on database:'+str(devInActive)+'\n')
                f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n'+'\n')

            # GeoFence information
            # Get summary information
            # Active Geos
            if valuesDict['includeSaveGeos']:
                f.write('Active GeoFences'+'\n')
                f.write('----------------'+'\n')
                geoActiveCount = 0
                geoInActiveCount = 0
                for geo in indigo.devices.iter('self.iGeoFence'):

                    geoProps = geo.pluginProps
                    if geoProps['geoActive']:
                        geoActiveCount = geoActiveCount + 1
                        f.write(''+ geo.name.upper()+'\n')
                        f.write('Latitude:'+str(geoProps['geoLatitude'])+' Longitude:'+str(geoProps['geoLongitude'])+'\n')
                        useUnits = displayUnits()
                        f.write('Range:'+str(geoProps['geoRange'])+str(useUnits[1])+'\n')
                        f.write('Home GeoFence:'+str(geoProps['geoHome'])+' Nest GeoFence:'+str(geoProps['geoNEST'])+' '+'Power Saving Geofence:'+str(geoProps['geoPower'])+'\n')
                        f.write('Devices near:'+str(int(geo.states['devicesNear']))+' Devices in range:'+str(int(geo.states['devicesInRange']))+' Nest Devices in range:'+str(int(geo.states['devicesInNestRange']))+'\n')
                        devFoundInGeo = 0

                        for dev in indigo.devices.iter('self.iAppleDeviceAuto'):
                            # Devices in the GeoFence
                            if dev.states['deviceNearestGeoName'].upper() == geoProps['geoName'].upper():
                                devFoundInGeo = devFoundInGeo + 1
                                f.write('\t'+dev.name.upper()+'\n')

                        if geoActiveCount == 0:
                            f.write('** NONE **'+'\n')

                        f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------'+'\n')

                f.write('iFindStuff Active GeoFences on database:'+str(geoActiveCount)+'\n')
                f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n'+'\n')

                # Inactive GeoFences
                if valuesDict['includeSaveInactives']:
                    f.write('Inactive GeoFences'+'\n')
                    f.write('------------------'+'\n')
                    for geo in indigo.devices.iter('self.iGeoFence'):
                        geoProps = geo.pluginProps
                        if not geoProps['geoActive']:
                            geoInActiveCount = geoInActiveCount + 1
                            f.write(''+ geo.name.upper()+'\n')
                            f.write('Latitude:'+str(geoProps['geoLatitude'])+' Longitude:'+str(geoProps['geoLongitude'])+'\n')
                            useUnits = displayUnits()
                            f.write('Range:'+str(geoProps['geoRange'])+str(useUnits[1])+'\n')
                            f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------'+'\n')

                    f.write('iFindStuff Inactive GeoFences on database:'+str(geoInActiveCount)+'\n')
                    f.write('------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n'+'\n')
                return True

        except:
            errorHandler('iSavePrint')

        return True

    def databasePurge(self, valuesDict=None, typeId=0):

        global iTrackHistory, db

        # Clears all tracking data
        if valuesDict['purgeData']:
            indigo.server.log('** Tracking data deleted **')
            db.purge()
        return True
