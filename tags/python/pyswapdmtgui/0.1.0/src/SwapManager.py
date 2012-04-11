#########################################################################
#
# SwapManager
#
# Copyright (c) 2011 Daniel Berenguer <dberenguer@usapiens.com>
#
# This file is part of the panStamp project.
#
# panStamp  is free software; you can redistribute it and/or modify
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
__date__ ="$Aug 21, 2011 4:30:47 PM$"
#########################################################################

from MainFrame import MainFrame

from SwapInterface import SwapInterface
from swap.SwapDefs import SwapState
from SwapException import SwapException

import wx
from wx.lib.pubsub import Publisher


class SwapManager(SwapInterface):
    """
    SWAP Management Class
    """
    def swapServerStarted(self):
        """
        SWAP server started successfully
        """
        self.dmtframe.cbServerStarted()

        # Display event
        wx.CallAfter(Publisher().sendMessage, "add_event", "SWAP server started")
    
    def newMoteDetected(self, mote):
        """
        New mote detected by SWAP server
        
        'mote'  Mote object
        """
        if self.dmtframe is not None:               
            # Display event
            evntext = "New mote with address " + str(mote.address) + " : " + mote.definition.product + \
            " (by " + mote.definition.manufacturer + ")"
            wx.CallAfter(Publisher().sendMessage, "add_event", evntext)
            
            # Append mote to the browsing tree
            wx.CallAfter(Publisher().sendMessage, "add_mote", mote)


    def newEndpointDetected(self, endpoint):
        """
        New endpoint detected by SWAP server
        
        'endpoint'  Endpoint object
        """
        if self.dmtframe is not None:
            # Display event
            evntext = "New endpoint with Reg ID = " + str(endpoint.getRegId()) + " : " + endpoint.name
            wx.CallAfter(Publisher().sendMessage, "add_event", evntext)


    def moteStateChanged(self, mote):
        """
        Mote state changed
        
        'mote' Mote object
        """
        if self.dmtframe is not None:
            # Display event
            evntext = "Mote with address " + str(mote.address) + " switched to \"" + \
                SwapState.toString(mote.state) + "\""
            wx.CallAfter(Publisher().sendMessage, "add_event", evntext)
            
            # SYNC mode entered?
            if mote.state == SwapState.SYNC:
                wx.CallAfter(Publisher().sendMessage, "sync_received", mote)


    def moteAddressChanged(self, mote):
        """
        Mote address changed
        
        'mote'  Mote object
        """
        if self.dmtframe is not None:
            # Display event
            evntext = "Mote changed address to " + str(mote.address)
            wx.CallAfter(Publisher().sendMessage, "add_event", evntext)
                
            # Update address in tree
            wx.CallAfter(Publisher().sendMessage, "changed_addr", mote)


    def endpointValueChanged(self, endpoint):
        """
        Endpoint value changed
        
        'endpoint' Endpoint object
        """
        if self.dmtframe is not None:
            # Display event
            evntext = endpoint.name + " in address " + str(endpoint.getRegAddress()) + " changed to " + endpoint.getValueInAscii()
            wx.CallAfter(Publisher().sendMessage, "add_event", evntext)

            # Update value in SWAP dmtframe
            wx.CallAfter(Publisher().sendMessage, "changed_val", endpoint)    


    def paramValueChanged(self, param):
        """
        Config parameter value changed
        
        'param' Config parameter object
        """
        if self.dmtframe is not None:
            # Display event
            evntext = param.name + " in address " + str(param.getRegAddress()) + " changed to " + param.getValueInAscii()
            wx.CallAfter(Publisher().sendMessage, "add_event", evntext)
                
            # Update value in SWAP dmtframe
            wx.CallAfter(Publisher().sendMessage, "changed_val", param) 
        

    def terminate(self):
        """
        Exit application
        """
        self.app.Exit()
        self.app.ExitMainLoop()


    def __init__(self, verbose=False):
        """
        Class constructor
        
        'verbose'  Print out SWAP frames or not
        """
        # Callbacks not being used
        self.registerValueChanged = None

        # wxPython app
        self.app = wx.PySimpleApp(0)
        wx.InitAllImageHandlers()
               
        # Start SWAP server
        try:
            # Superclass call
            SwapInterface.__init__(self, None, verbose, False)  
            # Clear error file
            SwapException.clear()         
        except SwapException as ex:
            ex.display()
            ex.log()

        # Open SWAP Device Management Tool
        self.dmtframe = MainFrame("SWAP Device Management Tool", self, server=self.server)
        #self.dmtframe.SetSize(wx.Size(370,500))
        self.app.SetTopWindow(self.dmtframe)
        self.dmtframe.CenterOnScreen()
        self.dmtframe.Show(True)

        self.app.MainLoop()