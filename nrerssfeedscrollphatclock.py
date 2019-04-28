#!/usr/bin/env python

import configparser
import datetime as dt
import PyRSS2Gen
import sys
import pysftp
import time
import scrollphat as sp
# import scrollphattest as sp
import logging
import logging.config
from nredarwin.webservice import DarwinLdbSession

def toboolean(thevalue):
    if thevalue == "True":
        return True
    else:
        return False
    #endif
#enddef

try:

    sp.set_brightness(1)
    sp.set_rotate(True)

    sp.clear()
    sp.write_string("#-")
    time.sleep(0.1)


    config = configparser.ConfigParser()
    config.read(sys.argv[1])

    debuglogconfigfilename = config.get('general', 'debuglogconfigfilename')

    # load the logging configuration
    logging.config.fileConfig(debuglogconfigfilename)
    logging.debug("logging file configuration loaded from '%s'" % debuglogconfigfilename)

    # open the ConfigParser and read in the configuration file provided on the command line
    logging.debug("reading program configuration from '%s'" % sys.argv[1])
   
    crsfrom = config.get('station', 'crsfrom')
    crsdest = config.get('station', 'crsdest')

    refreshdelayseconds = config.getint('general', 'refreshdelayseconds')
    darwinurl = config.get('general', 'darwinurl')
    darwinapikey = config.get('general', 'darwinapikey')

    temp = config.get('general', 'activedays')
    daylist = list(temp.split(","))
    activedays = list(map(toboolean,daylist))
    starttimehour = config.getint('general', 'starttimehour')
    finishtimehour = config.getint('general', 'finishtimehour')

    localdirectory = config.get('local', 'directory')
    localfilename = config.get('local', 'filename')

    sftphostname = config.get('sftp', 'hostname')
    sftpusername = config.get('sftp', 'username')
    sftppassword = config.get('sftp', 'password')
    sftpdirectory = config.get('sftp', 'directory')
    
    # Open the session with the url and ID
    sp.clear()
    sp.write_string("-#")
    time.sleep(0.1)
    
    darwin_session = DarwinLdbSession(wsdl=darwinurl, api_key=darwinapikey)
    logging.debug("darwin session handle obtained %s" % str(darwin_session))

    # Set the count to the delay so that first time into the loop it triggers a refresh
    totalsecondswaited = refreshdelayseconds

    while True:

        # Only update when the timeperiod has expired
        if totalsecondswaited >= refreshdelayseconds:

            # reset the count and show that updates are being made
            totalsecondswaited=0
            sp.clear()
            sp.write_string("##")
            time.sleep(0.1)

            if activedays[dt.datetime.today().weekday()] == True:
                if dt.datetime.today().hour >= starttimehour and dt.datetime.today().hour <= finishtimehour:

                    departures = []

                    # retrieve departure and arrival board
                    from_board = darwin_session.get_station_board(crsfrom)
                    dest_board = darwin_session.get_station_board(crsdest)
                    logging.debug("retrieved latest departure and arrival board data")
                    
                    logging.debug("active day and hours")
                    logging.debug("Locating The next departures from %s [%s] calling at %s [%s]" % (from_board.location_name, from_board.crs, dest_board.location_name, dest_board.crs))

                    reporttitle = "Last Updated on %s" % time.strftime("%02H:%02M:%02S")

                    # Loop through services
                    for service in from_board.train_services:
                        service_details = darwin_session.get_service_details(service.service_id)

                        # loop through calling points
                        
                        for cp in service_details.subsequent_calling_points:
                            if (cp.crs == crsdest):
                                departures.append(PyRSS2Gen.RSSItem(
                                    title = "%s - departure at %s (%s)" % (reporttitle, service.std, service.etd.upper()),
                                    link = darwinurl,
                                    description = "'%s' arriving at %s (%s)" % (cp.location_name, cp.st, cp.et.upper()),
                                    guid = PyRSS2Gen.Guid(str(time.time())),
                                    pubDate = dt.datetime.now())
                                )
                            #endif
                        #endfor
                    #endfor

                    if len(departures) != 0:
                        rss = PyRSS2Gen.RSS2(
                            title = "National Rail",
                            link = darwinurl,
                            description = "The next departures from %s [%s] calling at %s [%s]" % (from_board.location_name, from_board.crs, dest_board.location_name, dest_board.crs),
                            lastBuildDate = dt.datetime.now(),
                            items = departures
                        )
                        
                        rss.write_xml(open(localdirectory + "/" + localfilename, "w"))

                        with pysftp.Connection(sftphostname, username=sftpusername, password=sftppassword) as sftp:
                            with sftp.cd(sftpdirectory):
                                sftp.put(localdirectory + "/" + localfilename)
                        
                        logging.debug("Latest departure information for %d records written to %s and uploaded to SFTP site" % (len(departures), localfilename))
                    else:
                        logging.debug("No Departures data found")
                    #endif
                else:
                    logging.debug("Not active for current hours %d" % dt.datetime.today().hour)
                #endif
            else:
                logging.debug("Not active for current day %d" % dt.datetime.today().weekday())
            #endif
        #endif

        # display the current time whilst waiting
        sp.clear()
        sp.write_string(time.strftime("%H:"), 0)
        time.sleep(2)
        sp.clear()
        sp.write_string(time.strftime(":%M"), 0)
        time.sleep(2)
        totalsecondswaited+=4

    #endwhile

#endtry

except Exception as e:
    print("ERROR - %s" % str(e))
    logging.error("ERROR - %s" % str(e))
#endexcept

except KeyboardInterrupt:
    print("\nKeyboard exception (Ctr+C) caught, exit forced.")
    logging.error("Keyboard exception (Ctr+C) caught, exit forced.")
    sp.clear()
    sys.exit(-1)
#endexcept
