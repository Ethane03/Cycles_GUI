#import numpy as np
#from PIL import Image, ImageTk
#from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#from matplotlib.figure import Figure
#from Phidget22.Phidget import *
#from Phidget22.Devices.VoltageRatioInput import *
#from Phidget22.Net import *
#import matplotlib.pyplot as plt
from datetime import datetime
import time
#import csv
#import serial
#from threading import Thread
#from multiprocessing import Process, Queue, Event
import logging
from mecom import MeCom, ResponseException
#from serial import SerialException
#from pathlib import Path
#import os
GET_COMMAND_TABLE = [
    {"id": 1200, "name": "Temperature is Stable", "format": "INT32"},
    {"id": 1000, "name": "Object Temperature", "format": "FLOAT32"},
    {"id": 1010, "name": "Target Object Temperature", "format": "FLOAT32"},
    {"id": 1020, "name": "Actual Output Current", "format": "FLOAT32"},
    {"id": 1021, "name": "Actual Output Voltage", "format": "FLOAT32"},
    {"id": 1011, "name": "Ramp Object Temperature", "format": "FLOAT32"}
]
SET_COMMAND_TABLE = [
    {"id": 3000, "name": "Target Object Temp (Set)", "format": "FLOAT32"},
    {"id": 3003, "name": "Coarse Temp Ramp", "format": "FLOAT32"},#This might not be the actual name, I cannot find it in the documentation
    {"id": 2010, "name": "Status", "format": "INT32"}
]
class MeerstetterTEC():
    """
    Controlling TEC devices via serial
    """
    def __init__(self, port = "COM3"):
        self.port = port
        self._session = None
        self._connect()
    def __exit__(self, exc_type, exc_value, traceback):
        print("Exiting TEC session")
        print("\nExecution type:", exc_type)
        print("\nExecution value:", exc_value)
        print("\nTraceback:", traceback)
        self._tear_down()
    def _tear_down(self):
        self.session().stop()
    def _connect(self):
        #open session
        self._session = MeCom(serialport=self.port)
        #device address
        self.address = self._session.identify()
        logging.info("Connected to", self.address)
        print(datetime.now(), "Temperature Controller Connected")
    def session(self):
        """
        Get the current running session
        """
        if self._session == None:
            self._connect()
        return self._session
    def get_data(self,channel):
        """
        Get the standard set of data on a specified channel
        """
        data_string = ""
        print(datetime.now(), "Getting data from TEC channel", channel)
        data_string += f"Data from TEC channel {channel}\n"
        #getting data
        obj_temp = self.session().get_parameter(parameter_name="Object Temperature",address = self.address,parameter_instance = channel)
        set_temp = self.session().get_parameter(parameter_name="Target Object Temperature",address = self.address,parameter_instance = channel)
        current = self.session().get_parameter(parameter_name="Actual Output Current",address = self.address,parameter_instance = channel)
        voltage = self.session().get_parameter(parameter_name="Actual Output Voltage",address = self.address,parameter_instance = channel)
        temp_ramp = 60*self.session().get_parameter(parameter_id=3003,address = self.address,parameter_instance = channel)
        nominal_object_temp = self.session().get_parameter(parameter_id=1011,address = self.address,parameter_instance = channel)
        #formatting data
        data_string +=  "-----\n"
        data_string += f"Object temp = {obj_temp:.2f} °C\n"
        data_string += f"Set temp = {set_temp} °C\n"
        data_string += f"Nominal object temp = {nominal_object_temp:.2f} °C/min\n"
        data_string += f"Ramp rate = {temp_ramp:.4f} °C/min\n"
        data_string += f"Current = {current:.2f} A\n"
        data_string += f"Voltage = {voltage:.2f} V\n"
        data_string += f"Power = {current*voltage:.2f} W\n"
        print(data_string)
        return data_string
    def get_temp(self,channel):
        return self.session().get_parameter(parameter_name="Object Temperature",address = self.address,parameter_instance = channel)
    def get_electric(self,channel):
        current = self.session().get_parameter(parameter_name="Actual Output Current",address = self.address,parameter_instance = channel)
        voltage = self.session().get_parameter(parameter_name="Actual Output Voltage",address = self.address,parameter_instance = channel)
        return current, voltage
    def get_status(self, channel):
        """
        Get the status (on or off) of a specified channel
        """
        try:
            return self.session().get_parameter(parameter_name = "Status", address = self.address, parameter_instance = channel)
        except ResponseException as e:
            print("Error:", e)
    def set_temp(self, value, channel):
        """
        Set the temperature for a specified channel
        Value must be a float
        """
        #assertion to explicitly enter floats
        try:
            assert type(value) == float
            logging.info(f"Set object temperature for channel {channel} to {value} °C")
            return self.session().set_parameter(parameter_name="Target Object Temp (Set)", value=value,address = self.address,parameter_instance = channel)
        except ResponseException as e:
            print("Error:", e)
    def set_ramp_rate(self, value, channel):
        """
        Set the ramp rate for a specified channel
        Value must be a float
        Controller takes C/sec, but user side is C/min
        """
        #assertion to explicitly enter floats
        try:
            assert type(value) == float
            print(f"Set object temperature ramp rate for channel {channel} to {value} °C/min")
            return self.session().set_parameter(parameter_id=3003, value=value/60,address = self.address,parameter_instance = channel)
        except ResponseException as e:
            print("Error:", e)     
    def set_ramp_proximity(self, value, channel):
        """
        Set the ramp rate accuracy? for a specified channel
        Value must be a float
        Controller takes C/sec, but user side is C/min
        """
        #assertion to explicitly enter floats
        try:
            assert type(value) == float
            print(f"Set temperature ramp rate proximity for channel {channel} to {value} °C")
            return self.session().set_parameter(parameter_id=3002, value=value,address = self.address,parameter_instance = channel)
        except ResponseException as e:
            print("Error:", e) 
    def _set_enable(self,channel,enable = True):
        """
        Set the status (on or off) for a specified channel
        """
        value,description = (1,"on") if enable else (0,"off")
        logging.info(f"Set loop for channel {channel} to {description}")
        return self.session().set_parameter(parameter_name = "Status",value=value, address= self.address, parameter_instance = channel)
    def enable(self, channel):
        """
        Enable a channel
        """
        try:
            x = self._set_enable(channel, True)
            print(datetime.now(), f"TEC channel {channel} turned ON")
            return x
        except ResponseException as e:
            print("Error:", e)
    def disable(self, channel):
        """
        Disable a channel
        """
        try:
            x = self._set_enable(channel, False)
            print(datetime.now(), f"TEC channel {channel} turned OFF")
            return x
        except ResponseException as e:
            print("Error:", e)
    def reset_device(self):
        """
        Reset the TEC 
        """
        try:
            x = self.session().reset_device()
            print(datetime.now(), "TEC Reset")
            return x
        except ResponseException as e:
            print("Error:", e)