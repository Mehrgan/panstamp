#########################################################################
#
# MainFrame
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
__author__="Daniel Berenguer (dberenguer@usapiens.com)"
__date__ ="$Sep 16, 2011 10:46:15 AM$"
__appname__ = "SWAPdmt (GUI version)"
__version__ = "1.0"
#########################################################################

from DeviceSelector import DeviceSelector
from ParamDialog import ParamDialog
from WaitDialog import WaitDialog
from SerialDialog import SerialDialog
from NetworkDialog import NetworkDialog

from swap.SwapDefs import SwapType, SwapState
from SwapException import SwapException
from xmltools.XmlDevice import XmlDeviceDir
from xmltools.XmlSettings import XmlSettings
from xmltools.XmlNetwork import XmlNetwork

import time, sys

import wx.lib.agw.aui as aui
from wx.lib.pubsub import Publisher
import wx


class MainFrame(wx.Frame):
    '''
    Main GUI frame
    '''
    def __init__(self, title, parent=None, server=None):
        '''
        Constructor
        
        @param title: Title of the GUI frame
        @param parent: parent object
        @param server: SWAP server
        '''
        wx.Frame.__init__(self, None, wx.ID_ANY, title=title, size=(800,500))    

        favicon = wx.Icon("images/swap.ico", wx.BITMAP_TYPE_ICO, 16, 16)
        self.SetIcon(favicon)

        # Parent
        self.parent = parent
        # SWAP server
        self.server = server
        # Server startup dialog
        self._waitfor_startdialog = None
        
        # Sync dialog
        self._waitfor_syncdialog = None
        # Mote in SYNC mode
        self._moteinsync = None
               
        # Create menu bar
        self.menubar = wx.MenuBar()
        # Create menus
        menufile = wx.Menu()
        self.menugateway = wx.Menu()
        menudevices = wx.Menu()
        menuview = wx.Menu()
        menuhelp = wx.Menu()
        # Append items into the menus
        # File menu
        menufile.Append(101, "&Close", "Close SWAP Browser")
        
        # Gateway menu
        self.menugateway.Append(201, "&Connect", "Connect serial gateway")
        self.menugateway.Append(202, "&Disconnect", "Disconnect serial gateway")
        self.menugateway.Append(203, "&Serial port", "Configure gateway\'s serial port")
        self.menugateway.Append(204, "&Network", "Configure gateway\'s network settings")
        
        # Devices menu
        menudevices.Append(301, "&Network settings", "Configure network settings")
        menudevices.Append(302, "&Custom settings", "Configure custom settings")
        
        # Devices menu
        menuview.Append(401, "&Network monitor", "SWAP network monitor")
        
        # Help menu
        menuhelp.Append(501, "&About", "About this application")

        self.menubar.Append(menufile, "&File")
        self.menubar.Append(self.menugateway, "&Gateway")
        self.menubar.Append(menudevices, "&Devices")
        self.menubar.Append(menuhelp, "&Help")
        
        # Set menubar
        self.SetMenuBar(self.menubar)   

        # Disable Disconnect item. Enable Connect item
        self.menugateway.Enable(202, enable=False)
        self.menugateway.Enable(201, enable=True)
        # Disable Device menu
        self.menubar.EnableTop(2, enable=False)  

        wSize = self.GetSize()        
        self.mgr = aui.AuiManager()
        # tell AuiManager to manage this frame
        self.mgr.SetManagedWindow(self)
        self.browser_panel = BrowserPanel(self, self.server.lstMotes)
        self.sniffer_panel = SnifferPanel(self)
        self.event_panel = EventPanel(self)

        self.mgr.AddPane(self.browser_panel, aui.AuiPaneInfo().Left().Layer(1).Caption("SWAP network").CaptionVisible(True).MinimizeButton(True).MaximizeButton(True).BestSize(wx.Size(wSize[0]*0.3, wSize[1])))
        self.mgr.AddPane(self.sniffer_panel, aui.AuiPaneInfo().Center().Layer(2).Caption("Wireless packets").CaptionVisible(True).MinimizeButton(True).MaximizeButton(True).BestSize(wx.Size(wSize[0]*0.7, wSize[1]*0.7)))
        self.mgr.AddPane(self.event_panel, aui.AuiPaneInfo().Bottom().Caption("Network events").CaptionVisible(True).MinimizeButton(True).MaximizeButton(True).BestSize(wx.Size(wSize[0]*0.7, wSize[1]*0.3)))
  
        # Attach event handlers
        wx.EVT_MENU(self, 201, self._OnConnect)
        wx.EVT_MENU(self, 202, self._OnDisconnect)
        wx.EVT_MENU(self, 203, self._OnSerialConfig)
        wx.EVT_MENU(self, 204, self._OnGatewayNetworkConfig)
        wx.EVT_MENU(self, 301, self.onMoteNetworkConfig)
        wx.EVT_MENU(self, 302, self.onConfigDevice)
        wx.EVT_MENU(self, 501, self._OnAbout)
        wx.EVT_MENU(self, 101, self._OnClose)
        self.Bind(wx.EVT_CLOSE, self._OnCloseWindow)
  
        self.mgr.Update()
        self.SetAutoLayout(True)
        self.SetSize((800, 600))
        self.Layout()   

        # Create a pubsub receivers
        Publisher().subscribe(self.cb_add_event, "add_event")
        Publisher().subscribe(self.cb_add_mote, "add_mote")
        Publisher().subscribe(self.cb_changed_addr, "changed_addr")
        Publisher().subscribe(self.cb_changed_val, "changed_val")


    def cb_add_event(self, msg):
        """
        Request from SWAP server thread to add event to the event display
        
        @param msg: message containing the mote to be added to the tree
        """
        event = msg.data
        if isinstance(event, str):
            self.event_panel.print_event(event)
            
            
    def cb_add_mote(self, msg):
        """
        Request from SWAP server thread to add mote to the browser tree
        
        @param msg: message containing the mote to be added to the tree
        """
        mote = msg.data
        if mote.__class__.__name__ == "SwapMote":
            self.browser_panel.addMote(mote)
            
            
    def cb_changed_addr(self, msg):
        """
        Request from SWAP server thread to change a mote address from the browser tree
        
        @param msg: message containing the mote to be modified from the tree
        """
        mote = msg.data
        if mote.__class__.__name__ == "SwapMote":
            self.browser_panel.updateAddressInTree(mote)
            
            
    def cb_changed_val(self, msg):
        """
        Request from SWAP server thread to change an endpoint value from the browser tree
        
        @param msg: message containing the mote to be modified from the tree
        """
        endpoint = msg.data
        if endpoint.__class__.__name__ == "SwapEndpoint":
            self.browser_panel.updateEndpointInTree(endpoint)


    def _OnSerialConfig(self, evn):
        """
        Config serial port pressed
        """
        # Open serial port config dialog
        SerialDialog()
        
        
    def _OnGatewayNetworkConfig(self, evn):
        """
        Gateway->Network pressed. Callback function
        """
        # Configuration settings
        config = XmlNetwork(XmlSettings.network_file)
        # Open network config dialog
        if self.server.modem is None:
            dialog = NetworkDialog(self, config.devaddress, hex(config.network_id), config.freq_channel, config.security)
        else:
            dialog = NetworkDialog(self, self.server.modem.devaddress, hex(self.server.modem.syncword), self.server.modem.freq_channel, config.security)
        res = dialog.ShowModal()
        
        # Save new settings in xml file
        if res == wx.ID_CANCEL:
            return
        
        config.devaddress = int(dialog.devaddress)
        config.network_id = int(dialog.netid, 16)
        config.freq_channel = int(dialog.freq_channel)
        config.security = int(dialog.security)
        config.save()
        
        self._Info("In order to take the new settings, you need to restart the gateway", "Gateway restart required")
                  
       
    def _OnConnect(self, evn=None):
        """
        Connect option pressed
        """
        if self.server is None:
            return
           
        try:
            # Start SWAP server
            self.server.start()
            
            self._waitfor_startdialog = WaitDialog(self, "Connecting to SWAP network...", 10)
            if not self._waitfor_startdialog.show():
                # Stop SWAP server
                if self.server is not None:
                    self.server.stop()
                self._Warning("Unable to start SWAP server. Please check connection and try again.")
                return

            netid = self.server.getNetId()
            # Build tree
            self.browser_panel.build_tree(netid)
            
            self.menugateway.Enable(201, enable=False)
            self.menugateway.Enable(202, enable=True)
            self.menubar.EnableTop(2, enable=True)
            
        except SwapException as ex:
            self._Warning(ex.description)
            ex.log()


    def _OnDisconnect(self, evn):
        """
        Disconnect option pressed
        """
        # Stop SWAP server
        if self.server is not None:
            self.server.stop()
            
        WaitDialog(self, "Disconnecting from SWAP network...", 3).show()    
        
        self.menugateway.Enable(201, enable=True)
        self.menugateway.Enable(202, enable=False)
        self.menubar.EnableTop(2, enable=False)
        
        self._Info("Server stopped and disconnected from SWAP network", caption = "Disconnected")


    def cbServerStarted(self):
        """
        Callback function called from SwapManager when the SWAP sever has been
        successfully started
        """
        if self._waitfor_startdialog is not None:
            self._waitfor_startdialog.close()
              
        
    def syncReceived(self, mote):
        """
        SYNC signal received
        
        @param mote  Mote having entered the SYNC mode
        """
        if self._waitfor_syncdialog is not None:
            self._moteinsync = mote
            self._waitfor_syncdialog.close()
             
    
    def _Warning(self, message, caption = "Warning!"):
        """
        Display warning message
        """
        dialog = wx.MessageDialog(self, message, caption, wx.OK | wx.ICON_WARNING)
        dialog.ShowModal()
        dialog.Destroy()


    def _Info(self, message, caption = "Attention!"):
        """
        Show Information dialog with custom message
        """
        dialog = wx.MessageDialog(self, message, caption, wx.OK | wx.ICON_INFORMATION)
        dialog.ShowModal()
        dialog.Destroy()


    def waitForSync(self):
        """
        Show Waiting dialog and wait until a SYNC message is received
        """
        self._waitfor_syncdialog = WaitDialog(self, "Please, put your device in SYNC mode")
        result = self._waitfor_syncdialog.ShowModal() != wx.ID_CANCEL
        self._waitfor_syncdialog.Destroy()
        self._waitfor_syncdialog = None
        return result
           

    def _YesNo(self, question, caption = 'Yes or no?'):
        """
        Show YES/NO dialog with custom question
        """
        dialog = wx.MessageDialog(self, question, caption, wx.YES_NO | wx.ICON_QUESTION)
        result = dialog.ShowModal() == wx.ID_YES
        dialog.Destroy()
        return result


    def _OnAbout(self, evn):
        """
        Show About dialog
        """
        info = wx.AboutDialogInfo()
        info.SetIcon(wx.Icon('images/swapdmt.png', wx.BITMAP_TYPE_PNG))
        info.SetName(__appname__)
        info.SetVersion(__version__)
        info.SetDescription("SWAp Device Management Tool")
        info.SetCopyright('(C) 2011 panStamp')
        info.SetWebSite("http://www.panstamp.com")
        info.SetLicence("General Public License (GPL) version 2")
        info.AddDeveloper(__author__)
        wx.AboutBox(info)

        
    def _OnClose(self, evn):
        """
        Close browser
        """
        self.Close(True)


    def _OnCloseWindow(self, evn):
        """
        Callback function called whenever the window is closed
        """
        if self.server is not None:
            self.server.stop()
        self.Destroy()
        self.parent.terminate()
        
        
    def onMoteNetworkConfig(self, evn):
        """
        Devices->Network settings pressed. Callback function
        """
        paramsOk = False
        # Configuration settings
        config = XmlNetwork(XmlSettings.network_file)
        
        # This is our mote
        mote = None
        
        # Any mote selected from the tree?
        itemID = self.browser_panel.tree.GetSelection()
        if itemID is not None:
            obj = self.browser_panel.tree.GetPyData(itemID)
            if obj.__class__.__name__ == "SwapMote":
                mote = obj
                address = mote.address
                netid = config.network_id
                freqChann = config.freq_channel
                secu = mote.security
                if mote.pwrdownmode == True:
                    txinterval = mote.txinterval
                    mote = None
                else:
                    txinterval = None
                paramsOk = True

        # No mote selected from the tree?
        if not paramsOk:
            address = 0xFF
            netid = config.network_id
            freqChann = config.freq_channel
            secu = config.security
            txinterval = ""
        
        # Open network config dialog
        dialog = NetworkDialog(self, address, hex(netid), freqChann, secu, txinterval)
        res = dialog.ShowModal()

        if res == wx.ID_CANCEL:
            return
              
        # No mote selected?
        if mote is None:
            # Ask for SYNC mode
            res = self.waitForSync()
            if not res:
                return
            mote = self._moteinsync  
        
        # Send new config to mote
        if int(dialog.devaddress) != address:
            if not mote.setAddress(int(dialog.devaddress)):
                self._Warning("Unable to set mote's address")
        if dialog.netid != hex(netid):
            if not mote.setNetworkId(int(dialog.netid, 16)):
                self._Warning("Unable to set mote's Network ID")
        if int(dialog.security) != secu:
            if not mote.setSecurity(int(dialog.security)):
                self._Warning("Unable to set mote's security option")
        if dialog.interval is not None:
            if dialog.interval != txinterval:
                if not mote.setTxInterval(int(dialog.interval)):
                    self._Warning("Unable to set mote's Tx interval")
        if int(dialog.freq_channel) != freqChann:
            if not mote.setFreqChannel(int(dialog.freq_channel)):
                self._Warning("Unable to set mote's frequency channel")
                

    def onConfigDevice(self, evn):
        """
        Devices->Custom settings pressed. Callback function
        """
        isok = False
        # Any mote selected from the tree?
        itemID = self.browser_panel.tree.GetSelection()
        if itemID is not None:
            obj = self.browser_panel.tree.GetPyData(itemID)
            if obj.__class__.__name__ == "SwapMote":
                isok = True
            elif obj.__class__.__name__ == "SwapRegister":
                if obj.isConfig():
                    isok = True
                 
        if not isok:
            selector = DeviceSelector()
            res = selector.ShowModal()
            
            if res == wx.ID_CANCEL:
                return
            
            option = selector.getSelection()                    
            selector.Destroy()       
            # Get Develoepr/device directory from devices.xml
            devicedir = XmlDeviceDir()
            # Find our mote within the directory
            obj = devicedir.getDeviceDef(option)
            if obj is None:
                self._Warning("Unable to find device \"" + option + "\" in directory")
                return
            
        # Configure registers
        self._configReg(obj)


    def _configReg(self, obj):
        """
        Configure registers in mote
        
        @param obj:  Mote or parameter to be configured
        """
        if obj is not None:
            if obj.__class__.__name__ == "XmlDevice":
                mote = None
                regs = obj.getRegList(True)
                if regs is not None:
                    for reg in regs:                        
                        dialog = ParamDialog(self, reg)                        
                        dialog.Destroy()
                    # Does this device need to enter SYNC mode first?
                    if obj.pwrdownmode == True:
                        res = self.waitForSync()                        
                        if not res:
                            return
                        mote = self._moteinsync           
                    # Send new configuration to mote
                    if mote is not None:
                        for reg in regs:
                            if mote.cmdRegisterWack(reg.id, reg.value) == False:
                                self._Warning("Unable to set register \"" + reg.name + "\" in device " + str(reg.getAddress()))
                                break
            elif obj.__class__.__name__ == "SwapMote":
                mote = obj
                if mote.lstcfgregs is not None:
                    for reg in mote.lstcfgregs:
                        dialog = ParamDialog(self, reg)
                        dialog.Destroy()
                    # Does this device need to enter SYNC mode first?
                    if mote.definition.pwrdownmode == True:
                        res = self.waitForSync()
                        if not res:
                            return
                        mote = self._moteinsync           
                    # Send new configuration to mote
                    if mote is not None:
                        for reg in mote.lstcfgregs:
                            if mote.cmdRegisterWack(reg.id, reg.value) == False:
                                self._Warning("Unable to set register \"" + reg.name + "\" in device " + str(reg.getAddress()))
                                break              
            elif obj.__class__.__name__ == "SwapRegister":
                dialog = ParamDialog(self, obj)
                dialog.Destroy()
                mote = obj.mote
                # Does this device need to enter SYNC mode first?
                if mote.definition.pwrdownmode == True:
                    res = self.waitForSync()
                    if not res:
                        return
                    mote = self._moteinsync
                    
                # Send new configuration to mote
                if mote is not None:
                    if mote.cmdRegisterWack(obj.id, obj.value) == False:
                        self._Warning("Unable to set register \"" + obj.name + "\" in device " + str(obj.getAddress()))
            
            # Mote still in SYNC mode?
            if self._moteinsync is not None:
                if self._moteinsync.state == SwapState.SYNC:
                    # Leave SYNC mode
                    self._moteinsync.leaveSync()
                    self._moteinsync = None
                    
        
class BrowserPanel(wx.Panel):
    """
    GUI panel containing the SWAP network tree
    """
    def _RightClickCb(self, evn):
        """
        Mouse right-click event. Callback function
        """
        # Get item currently selected
        itemID = self.tree.GetSelection()
        obj = self.tree.GetPyData(itemID)
        menu = None
        if obj.__class__.__name__ == "SwapMote":
            menu = wx.Menu()                
            menu.Append(0, "Network settings")
            wx.EVT_MENU(menu, 0, self.parent.onMoteNetworkConfig)
            if obj.lstcfgregs is not None:
                menu.Append(1, "Custom settings")
                wx.EVT_MENU(menu, 1, self.parent.onConfigDevice)
        elif obj.__class__.__name__ == "SwapRegister":
            if obj.isConfig():
                menu = wx.Menu()
                menu.Append(0, "Configure")
        
        if menu is not None:
            self.PopupMenu(menu, evn.GetPoint())
            menu.Destroy()   
              

    def addMote(self, mote):
        """
        Add mote to the tree
        
        'mote'  Mote to be added to the tree
        """
        # Add mote to the root
        moteid = self.tree.AppendItem(self.rootid, "Mote " + str(mote.address) + ": " + mote.definition.product)
        self.tree.SetItemImage(moteid, self.moteIcon, wx.TreeItemIcon_Normal)
        # Associate mote with its tree entry
        self.tree.SetPyData(moteid, mote)

        if mote.lstcfgregs is not None:
            # Append associated config registers
            for reg in mote.lstcfgregs:
                # Add register to the mote item
                regID = self.tree.AppendItem(moteid, "Register " + str(reg.id) + ": " + reg.name)
                self.tree.SetItemImage(regID, self.cfgRegIcon, wx.TreeItemIcon_Normal)
                # Associate register with its tree entry
                self.tree.SetPyData(regID, reg)
                # Append associated parameters
                for param in reg.lstItems:
                    # Add register to the mote item
                    paramID = self.tree.AppendItem(regID, param.name + " = " + param.getValueInAscii())
                    self.tree.SetItemImage(paramID, self.cfgParamIcon, wx.TreeItemIcon_Normal)
                    # Associate register with its tree entry
                    self.tree.SetPyData(paramID, param)
        if mote.lstregregs is not None:
            # Append associated regular registers
            for reg in mote.lstregregs:
                # Add register to the mote item
                regID = self.tree.AppendItem(moteid, "Register " + str(reg.id) + ": " + reg.name)
                self.tree.SetItemImage(regID, self.regRegIcon, wx.TreeItemIcon_Normal)
                # Associate register with its tree entry
                self.tree.SetPyData(regID, reg)
                # Append associated endpoints
                for endp in reg.lstItems:
                    # Add register to the mote item
                    endpID = self.tree.AppendItem(regID, endp.name + " = " + endp.getValueInAscii())
                    if endp.direction == SwapType.OUTPUT:
                        self.tree.SetItemImage(endpID, self.outputIcon, wx.TreeItemIcon_Normal)
                    else:
                        self.tree.SetItemImage(endpID, self.inputIcon, wx.TreeItemIcon_Normal)
                    # Associate register with its tree entry
                    self.tree.SetPyData(endpID, endp)
                  

    def updateEndpointInTree(self, endpoint):
        """
        Update endpoint value in tree
        
        @param endpoint:  Endpoint to be updated in the tree
        """
        moteid, motecookie = self.tree.GetFirstChild(self.rootid)
        
        while moteid.IsOk():
            mote = self.tree.GetPyData(moteid)
            if mote.address == endpoint.getRegAddress():
                regid, regcookie = self.tree.GetFirstChild(moteid)
                while regid.IsOk():
                    reg = self.tree.GetPyData(regid)
                    if reg.id == endpoint.getRegId():
                        endpid, endpcookie = self.tree.GetFirstChild(regid)
                        while endpid.IsOk():
                            endp = self.tree.GetPyData(endpid)
                            if endp.name == endpoint.name:
                                # Get endpoint icon
                                icon = self.tree.GetItemImage(endpid)
                                # Append new endpoint to the tree
                                new_endpid = self.tree.InsertItem(regid, endpid, text=endpoint.name + " = " + endpoint.getValueInAscii(), image=icon)
                                self.tree.SetPyData(new_endpid, endp)
                                # Remove old endpoint
                                self.tree.Delete(endpid)
                                return
                            endpid, endpcookie = self.tree.GetNextChild(regid, endpcookie)
                        return
                    regid, regcookie = self.tree.GetNextChild(moteid, regcookie)
                return
            moteid, motecookie = self.tree.GetNextChild(self.rootid, motecookie)
            
            
    def updateAddressInTree(self, mote):
        """
        Update mote address in tree
        
        @param mote  Mote to be updated in the tree
        """
        # Try with first mote in tree
        moteid, motecookie = self.tree.GetFirstChild(self.rootid)
        
        while moteid.IsOk():
            m = self.tree.GetPyData(moteid)
            if m == mote:                
                # Add mote to the root
                new_moteid = self.tree.AppendItem(self.rootid, "Mote " + str(mote.address) + ": " + mote.definition.product)
                self.tree.SetItemImage(new_moteid, self.moteIcon, wx.TreeItemIcon_Normal)
                # Associate mote with its tree entry
                self.tree.SetPyData(new_moteid, mote)                
                # Remove old mote
                self.tree.Delete(moteid)
                return
            
            # Try with next mote in tree
            moteid, motecookie = self.tree.GetNextChild(self.rootid, motecookie)
                              
                            
    def build_tree(self, netid):
        '''
        Build SWAP tree
        
        @param netid: SWAP network ID
        '''                 
        if netid is not None:
            rootStr = "SWAP network " + hex(netid)
        else:
            rootStr = "SWAP network"
      
        # Clear tree
        self.tree.DeleteAllItems()
        self.rootid = self.tree.AddRoot(rootStr)
        self.tree.SetPyData(self.rootid, None)

        for mote in self.lstmotes:
            self.addMote(mote)
 
        self.tree.SetItemImage(self.rootid, self.rootIcon, wx.TreeItemIcon_Normal)
 
        self.tree.Expand(self.rootid)
        
        # Right-click event
        wx.EVT_TREE_ITEM_RIGHT_CLICK(self.tree, -1, self._RightClickCb)
        
        
    def __init__(self, parent, lstmotes):
        """
        Class constructor
        
        @param parent: parent object
        @param lstmotes: List of motes
        """
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        
        ## Parent frame
        self.parent = parent
        ## List of motes
        self.lstmotes = lstmotes
        ## SWAP browsing tree
        self.tree = wx.TreeCtrl(self, -1, style=wx.TR_HAS_BUTTONS|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.tree, 1, wx.EXPAND)

        ## Create image list:
        il = wx.ImageList(16, 16)
        self.rootIcon = il.Add(wx.Bitmap("images/network.ico", wx.BITMAP_TYPE_ICO))
        self.moteIcon = il.Add(wx.Bitmap("images/swap.ico", wx.BITMAP_TYPE_ICO))
        self.regRegIcon = il.Add(wx.Bitmap("images/database.ico", wx.BITMAP_TYPE_ICO))
        self.cfgRegIcon = il.Add(wx.Bitmap("images/cfgreg.ico", wx.BITMAP_TYPE_ICO))
        self.cfgParamIcon = il.Add(wx.Bitmap("images/cfgparam.ico", wx.BITMAP_TYPE_ICO))
        self.inputIcon = il.Add(wx.Bitmap("images/input.ico", wx.BITMAP_TYPE_ICO))
        self.outputIcon = il.Add(wx.Bitmap("images/output.ico", wx.BITMAP_TYPE_ICO))
        self.tree.AssignImageList(il)

        self.SetAutoLayout(True)
        self.SetSizer(sizer)


class SnifferPanel(wx.Panel):
    """
    GUI panel displaying the SWAP network traffic
    """
    def write(self, text):
        """
        Add new line into the log window
        
        @param text: Text string to be displayed in the log window
        """
        if text:
            if len(text) > 1: # Condition added to avoid printing single white spaces
                if text.startswith("Rved: "):                    
                    msg = text[6:]
                    msgtype = self.get_message_type(msg)
                    if msgtype is None:
                        return
                    image = self.arrow_left_icon
                elif text.startswith("Sent: "):
                    msgtype = "sent"
                    msg = text[6:-1]
                    msgtype = self.get_message_type(msg)
                    if msgtype is None:
                        return
                    image = self.arrow_right_icon
                elif text.startswith("SwapException occurred: "):
                    msgtype = "ERROR"
                    msg = text[24:]
                    image = self.warning_icon
                else:
                    return

                index = self.log_list.GetItemCount()
                self.log_list.InsertStringItem(index, str(time.time()))
                self.log_list.SetStringItem(index, 1, msgtype)
                self.log_list.SetStringItem(index, 2, msg)
                self.log_list.SetItemImage(index, image)
                self.log_list.EnsureVisible(index)

    
    def get_message_type(self, msg):
        """
        Get the type of message received or being sent
        
        @param msg: SWAP message
        
        @return Type of message in string format
        """
        if len(msg) < 14:
            return None

        if msg[0] == '(':
            if msg[5] == ')':
                shift = 6
            else:
                return None
        else:
            shift = 0
            
        msgtype = msg[8+shift:10+shift]

        if msgtype == "00":
            return "status"
        elif msgtype == "01":
            return "query"
        elif msgtype == "02":
            return "command"

        return None
    
    
    def _display_info(self):
        """
        Show Information dialog about the selected line
        """
        err = False
        # Get current selection from list
        index = self.log_list.GetFirstSelected()
        timestamp = self.log_list.GetItem(index, 0).GetText()
        msgtype = self.log_list.GetItem(index, 1).GetText()
        packet = self.log_list.GetItem(index, 2).GetText()
               
        text = "Time: " + timestamp + "\n"
        text += "Type of packet: " + msgtype + "\n"
        
        if packet[0] == '(':
            if packet[5] == ')':
                text += "RSSI: " + packet[1:3] + "\n"
                text += "LQI: " + packet[3:5] + "\n"
                shift = 6
            else:
                text = "Message malformed"
                err = True
        else:
            shift = 0
        
        if not err:
            destaddr = packet[shift:shift+2]
            if destaddr == "00":
                destaddr = "broadcast"
            text += "Destination address: " + destaddr + "\n"
            text += "Source address: " + packet[shift+2:shift+4] + "\n"
            text += "Transmission hop: " + packet[shift+4:shift+5] + "\n"
            text += "Security: " + packet[shift+5:shift+6] + "\n"
            text += "Security nonce: " + packet[shift+6:shift+8] + "\n"
            text += "Register address: " + packet[shift+10:shift+12] + "\n"
            text += "Register ID: " + packet[shift+12:shift+14] + "\n"
            if len(packet) > 14:
                text += "Register value: " + packet[shift+14:] + "\n"
        
        dialog = wx.MessageDialog(self, text, "Details", wx.OK | wx.ICON_INFORMATION)
        dialog.ShowModal()
        dialog.Destroy()
        
        
    def _cb_right_click(self, evn):
        """
        Mouse right click on log list
        
        @param evn: Event received
        """
        index = self.log_list.GetFirstSelected()
        if index > -1:
            msgtype = self.log_list.GetItem(index, 1).GetText()
            if msgtype != "ERROR":        
                menu = wx.Menu()
                menu.Append(0, "Show details")
                wx.EVT_MENU(menu, 0, self._cb_on_details)
                self.PopupMenu(menu, evn.GetPoint())
                menu.Destroy()


    def _cb_on_details(self, evn):
        """
        Display packet details
        
        @param evn: Event received
        """
        self._display_info()


    def __init__(self, parent):
        """
        Class constructor
        
        @param parent: parent object
        """
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)

        # Create list box
        self.log_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
        self.log_list.ScrollList(10, 10)
        self.log_list.InsertColumn(0, "Timestamp")
        self.log_list.InsertColumn(1, "Type")
        self.log_list.InsertColumn(2, "Message")
        self.log_list.SetColumnWidth(0, 140)
        self.log_list.SetColumnWidth(1, 60)
        self.log_list.SetColumnWidth(2, 400)

        # create the image list:
        il = wx.ImageList(16, 16)
        self.arrow_left_icon = il.Add(wx.Bitmap("images/arrow_left.ico", wx.BITMAP_TYPE_ICO))
        self.arrow_right_icon = il.Add(wx.Bitmap("images/arrow_right.ico", wx.BITMAP_TYPE_ICO))
        self.warning_icon = il.Add(wx.Bitmap("images/warning.ico", wx.BITMAP_TYPE_ICO))
        self.log_list.AssignImageList(il, wx.IMAGE_LIST_SMALL)
        
        # Right-click event
        wx.EVT_LIST_ITEM_RIGHT_CLICK(self.log_list, -1, self._cb_right_click)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log_list, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        # Redirect stdout to the LogCtrl widget
        sys.stdout = RedirectText(self)


class EventPanel(wx.Panel):
    """
    GUI panel used to display SWAP events
    """
    def print_event(self, evntext):
        """
        Print event
        
        @param evntext: Event text to be printed out
        """
        timestamp = str(time.time())
        self.event_area.write(timestamp + ": " + evntext + "\n")
        
        
    def __init__(self, parent):
        """
        Class constructor
        
        @param parent: parent object
        """
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)

        # Create text area       
        self.event_area = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.event_area, 1, wx.EXPAND)
        self.SetSizer(sizer)
        

class RedirectText(object):
    """
    Class for redirecting text to a given widget
    """
    def __init__(self, widget):
        self.out = widget
 
    def write(self, string):
        if self.out is not None:
            wx.CallAfter(self.out.write, string)

                    
if __name__ == "__main__":
    app = wx.PySimpleApp()
    frame = MainFrame("SWAP Device Management Tool")
    frame.Show()
    app.MainLoop()
