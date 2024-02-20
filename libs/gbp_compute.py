#!/usr/bin/env python
# Copyright (c) 2016 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import logging
import re
import sys
import tempfile
import urllib.request, urllib.parse, urllib.error
import yaml
from fabric.api import cd,run,env, hide, get, settings,sudo,local
from fabric.contrib import files
from io import StringIO

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
           print("The desired file was NOT available in remote host")
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
            tenantName = '_%s_%s' %(apicSystemID,tenantName)
            if tenantName != rdconfig["domain-policy-space"]:
               print('Tenant Name is NOT in the rdconfig')
               return 0
            if len(subnets):
               unmatched = [subnet for subnet in subnets if subnet not in rdconfig["internal-subnets"]]
               if len(unmatched):
                    print('Following subnets are NOT in rdConfig file = %s' %(unmatched))
                    return 0
            if rtrID:
               if '_%s_%s' %(apicSystemID,rtrID) != rdconfig["domain-name"]:
                   print('VRF/domain-name is NOT in the rdconfig')
                   return 0
            return 1
        else:
            print('rdConfig file was NOT found in the Compute Node')
            return 0
    
    def verify_EpFile(self,portID,portMAC,**kwargs):
        """
        Verify the EP Files
        key = pass exact name string as it
        appears in the EP file with no '-' instead '_'
        example: vm-name , should be passed as vm_name
        """
        remoteFile = '/var/lib/opflex-agent-ovs/endpoints/%s_%s.ep' %(portID,portMAC)
        epfile = self.GetReadFiles(remoteFile)
        if epfile:
            for key, value in kwargs.items():
                if key == "vm_name":
                    if value != epfile["attributes"]["vm-name"]:
                         return None
                elif key == "ip_address_mapping":
                    if not len(epfile["ip-address-mapping"]):
                        return  None
                    else: #return the attributes
                        #epfile["ip-address-mapping"] is a list
                        for item in epfile["ip-address-mapping"]: 
                            #Incase of SNAT
                            if "next-hop-if" in list(item.keys()):
                               return item["next-hop-if"],\
                               item["policy-space-name"],\
                               item["endpoint-group-name"]
                            else: #Incase of DNAT
                                return item["floating-ip"],\
                                item["policy-space-name"],\
                                item["endpoint-group-name"]             
                else:
                    if '_' in key:
                      key = key.replace('_','-')
                    if key == 'ip':
                        if set(value) != set(epfile[key]):
                            print("Mismatch between user fed and epfile IP",\
                              value, epfile[key])
                            return None
                    else:
                        if value != epfile[key]:
                           print("Mismatch between user fed and epfile",\
                              value, epfile[key])
                           return None
            return True
        else:
            return None   
        
    def getSNATEp(self,L3OutName):
        """
        Verifies the content of SNAT EP
        """
        remoteFile = '/var/lib/opflex-agent-ovs/endpoints/%s.ep' %(L3OutName)
        epfile = self.GetReadFiles(remoteFile)
        if epfile:
            return epfile["interface-name"],\
                   epfile["ip"][0],\
                   epfile["policy-space-name"],\
                   epfile["endpoint-group-name"].split('|')[1],\
                   epfile["attributes"]["vm-name"]
        else:
            print("SNAT EP File NOT FOUND")
            return None
