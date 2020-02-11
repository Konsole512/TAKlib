#######################################################
# 
# point.py
# Python implementation of the Class point
# Generated by Enterprise Architect
# Created on:      11-Feb-2020 11:08:07 AM
# Original author: Corvo
# 
#######################################################


class point:
# default constructor       def __init__(self):  

    # Latitude referred to the WGS 84 ellipsoid in degrees
    lat = "43.97957317" 
     # lat getter 
     def getlat(self): 
      return self.lat 
 
     # lat setter 
     def setlat(lat=0):  
     self.lat=lat 
 
    # Longitude referred to the WGS 84 in degrees
    lon = "-66.07737696" 
     # lon getter 
     def getlon(self): 
      return self.lon 
 
     # lon setter 
     def setlon(lon=0):  
     self.lon=lon 
 
    # Circular 1-sigma or decimal a circular area about the point in meters
    ce = "9999999.0" 
     # ce getter 
     def getce(self): 
      return self.ce 
 
     # ce setter 
     def setce(ce=0):  
     self.ce=ce 
 
    # Linear 1-sigma error or an altitude range about the point in meters
    le = "9999999.0" 
     # le getter 
     def getle(self): 
      return self.le 
 
     # le setter 
     def setle(le=0):  
     self.le=le 
     