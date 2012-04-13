#########################################################################
#
# Copyright (c) 2012 Daniel Berenguer <dberenguer@usapiens.com>
#
# This file is part of the lagarto project.
#
# lagarto  is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# panStamp is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with panLoader; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
# USA
#
#########################################################################
__author__="Daniel Berenguer"
__date__  ="$Feb 24, 2012$"
#########################################################################

import ephem
import time

from lagartoresources import LagartoEndpoint
from xmltools import XmlSettings

from clouding import PachubePacket, ThingSpeakPacket


class TimeAPI:
    """
    Time API providing static methods
    """
    # Current time
    current_time = None

    # Clock event: True or False
    event = False
       
        
    @staticmethod
    def time():
        """
        Return hhmm value
        """
        return TimeAPI.current_time.tm_hour * 100 + TimeAPI.current_time.tm_min


    @staticmethod
    def date():
        """
        Return MMdd value
        """
        return TimeAPI.current_time.tm_mon * 100 + TimeAPI.current_time.tm_mday


    @staticmethod
    def month():
        """
        Return month [1-12] value
        """
        return TimeAPI.current_time.tm_mon


    @staticmethod
    def monthday():
        """
        Return month day [1-31] value
        """
        return TimeAPI.current_time.tm_mday


    @staticmethod
    def weekday():
        """
        Return week day [0-6] value
        """
        return TimeAPI.current_time.tm_wday


    @staticmethod
    def repeat_time(start_time, interval):
        """
        Repeat time condition a given amount of minutes
        
        @param start_time: initial time condition in hhmm format
        @param interval: periodic interval in hhmm format
        """
        if interval == 0:
            return start_time

        now = TimeAPI.time()
        
        t = start_time
        while True:
            if t == now:
                return now
            elif t == 2400 and now == 0:
                return 0
            elif t > 2400:
                return -1
            t += interval
            

    @staticmethod
    def sunrise():
        """
        Return sunrise time in hhmm format
        """
        observ = ephem.Observer()  
        observ.lat = str(XmlSettings.latitude)  
        observ.long = str(XmlSettings.longitude)  
        sun = ephem.Sun()  
        sun.compute()  
        st = ephem.localtime(observ.next_rising(sun))

        factor = 1
        if st.minute < 10:
            factor = 10
        return st.hour * 100 * factor + st.minute


    @staticmethod
    def sunset():
        """
        Return sunrise time in hhmm format
        """
        observ = ephem.Observer()  
        observ.lat = str(XmlSettings.latitude)  
        observ.long = str(XmlSettings.longitude)  
        sun = ephem.Sun()  
        sun.compute()  
        st = ephem.localtime(observ.next_setting(sun))

        factor = 1
        if st.minute < 10:
            factor = 10
        return st.hour * 100 * factor + st.minute

        
    @staticmethod
    def update_time():
        """
        Update current tine
        """
        TimeAPI.current_time = time.localtime()


class NetworkAPI:
    """
    Static toolbox for network data
    """
    # Lagarto client object
    lagarto_client = None
    # Current network event tuple (endpoint, value)
    event = [None, None]
      

    @staticmethod
    def reset_event():
        """
        Reset event variable
        """
        NetworkAPI.event = [None, None]

    @staticmethod
    def get_endpoint(endp):
        """
        Get Lagarto endpoint
        
        @param endp: endpoint identification string
        format 1: process.location.name
        format 2: process.id
        
        @return lagarto endpoint object
        """
        epd = endp.split('.')
        length = len(epd)
        epid = None
        eploc = None
        epname = None
        if length == 2:
            epid = epd[1]
        elif length == 3:
            eploc = epd[1]
            epname = epd[2]
        else:
            return None
        
        procname = epd[0]
        lagarto_endp = LagartoEndpoint(endp_id=epid, location=eploc, name=epname)

        status = NetworkAPI.lagarto_client.request_status(procname, [lagarto_endp.dumps()])
        if status is not None:
            if len(status) > 0:
                lagarto_endp = LagartoEndpoint(endpstr=status[0], procname=procname)
                return lagarto_endp
        return None


    @staticmethod
    def get_value(endp):
        """
        Get endpoint value
        
        @param endp: endpoint identification string
        format 1: process.location.name
        format 2: process.id
        
        @return endpoint value
        """
        epd = NetworkAPI.get_endpoint(endp)
        if epd is not None:
            return epd.value
        return None


    @staticmethod
    def set_value(endp, value):
        """
        Set endpoint value
        
        @param endp: endpoint identification string
        format 1: process.location.name
        format 2: process.id
        @param value: new endpoint value
        
        @return endpoint value
        """
        epd = NetworkAPI.get_endpoint(endp)
        if epd is not None:
            endp.value = value
            
            status = NetworkAPI.lagarto_client.request_status(procname, [lagarto_endp.dumps()])
            if status is not None:
                if len(status) > 0:
                    if "value" in status[0]:
                        return status[0]["value"]

        return None


    def __init__(self, lagarto_client):
        """
        Constructor
        
        @param lagarto_client: lagarto client object
        """
        NetworkAPI.lagarto_client = lagarto_client
        LagartoEndpoint.lagarto_client = lagarto_client


class CloudAPI:
    """
    Static toolbox for clouding tasks
    """
    @staticmethod
    def push_pachube(endp, sharing_key, feed_id, datastream_id):
        """
        Push data to pachube

        @param endp: endpoint identification string
        format 1: process.location.name
        format 2: process.id        
        @param sharing_key: Pachube sharing key
        @param feed_id: Pachube feed ID
        @param datastream_id: Pachube datastream ID
        
        @return HTTP response from Pachube
        """
        endpoint = NetworkAPI.get_endpoint(endp)
        if endpoint is not None:
            packet = PachubePacket(sharing_key, feed_id, [(datastream_id, endpoint.value)])
            return packet.push()
        return None


    @staticmethod
    def push_thingspeak(endp, api_key, field_id):
        """
        Push data to ThingSpeak

        @param endp: endpoint identification string
        format 1: process.location.name
        format 2: process.id        
        @param api_key: ThingSpeak API key
        @param field_id: ThingSpeak field ID
        
        @return HTTP response from ThingSpeak
        """
        endpoint = NetworkAPI.get_endpoint(endp)
        if endpoint is not None:
            packet = ThingSpeakPacket(api_key, [(field_id, endpoint.value)])
            return packet.push()
        return None

