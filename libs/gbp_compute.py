#!/usr/bin/env python
import json
import logging
import re
import sys
import tempfile
import urllib
import yaml
from fabric.api import cd,run,env, hide, get, settings,sudo,local
from fabric.contrib import files
from StringIO import StringIO

class Compute(object):

    def __init__(self,hostIp,username='root',password='noir0123'):
	self.host = hostIp
	self.username = username
	self.password = password

    def GetReadFiles(self,remotefilename):
	"""
	Fetches and reads the remote files from remote servers(Compute-nodes
        in this case)
	remotefilename: mention filename with path
	"""
	env.host_string = self.host
    	env.user = self.username
    	env.password = self.password
    	# Below commented out block is the simplest
    	# get and read of a remote file. Caveat: need
    	# to run the local to deleted the temp generated file
    	"""
    	get(remotefilename,'/tmp/f')
    	try:
           with open('tmp/f','rt') as fl:
           conf = yaml.load(fl)
    	finally:
           local('rm /tmp/f')
    	"""
    	# Use of tempfile module helps to create and delete
    	# the tempfile for get(). Used json to convert a 
    	# a string(containing dict pattern) to a dict. nice
    	# trick to learn
	try:
    	   with tempfile.TemporaryFile() as fd:
                get(remotefilename, fd)
                fd.seek(0)
                content = fd.read()
	except:
	   print "The desired file was NOT available in remote host"
	   return 0
        filedict = json.loads(content)
	return filedict

    def verify_rdConfig(self,tenantName,rtrID,tenantID='',subnets=[],apicSystemID='noirolab'):
	"""
        Verify the content of the rdConfig files
	rtrID: 'shared' or UUID. If 'shared',then pass tenantID
	subnets: pass it as list
	"""
	if rtrID == 'shared' and tenantID:
	   remotefilename = '/var/lib/opflex-agent-ovs/endpoints/%s.rdconfig' %(tenantID)
	if rtrID != 'shared':
	   remotefilename = '/var/lib/opflex-agent-ovs/endpoints/router:%s.rdconfig' %(rtrID)
	rdconfig = self.GetReadFiles(remotefilename)
	if isinstance(rdconfig,dict):
	    if tenantName != rdconfig["domain-policy-space"]:
	       print 'Tenant Name is NOT in the rdconfig'
	       return 0
	    if len(subnets):
	       unmatched = [subnet for subnet in subnets if subnet not in rdconfig["internal-subnets"]]
	       if len(unmatched):
		    print 'Following subnets are NOT in rdConfig file = %s' %(unmatched)
		    return 0
	    if rtrID:
	       if '_%s_%s' %(apicSystemID,rtrID) != rdconfig["domain-name"]:
                   print 'VRF/domain-name is NOT in the rdconfig'
	           return 0
	else:
	    print 'rdConfig file was NOT found in the Compute Node'
	    return 0
    
    def verify_EpFile(self,portID,**kwargs):
	"""
	Verify the EP Files
	key = pass exact name string as it
        appears in the EP file with no '-' instead '_'
	example: vm-name , should be passed as vm_name
	"""
	remoteFile = '/var/lib/opflex-agent-ovs/endpoints/%s.ep' %(portID)
	epfile = self.GetReadFiles(remoteFile)
	for key, value in kwargs.iteritems():
	    if key == "vm_name":
	        if value != epfile["attributes"]["vm-name"]:
		     return 0
	    elif key == "ip_address_mapping":
                if not len(epfile["ip-address-mapping"]):
		    return  0
	    else:
                if '_' in key:
                  key = key.replace('_','-')
	        if value != epfile["%s" %(key)]:
	           return 0
           

