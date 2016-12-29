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

import sys
from time import sleep
import logging
import string
import re
from fabric.api import cd,run,env, hide, get, settings
from gbp_utils import *

# Initialize logging
#logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
_log = logging.getLogger()
_log.setLevel(logging.INFO)

class gbpCfgCli(object):

    def __init__(self, controllerIp, cntrlr_username='root',
                 cntrlr_passwd='noir0123',tenant='admin',
                 rcfile = '/root/keystonerc_admin'):
      self.cntrlrip = controllerIp
      self.uname = cntrlr_username
      self.passwd = cntrlr_passwd
      self.tenant = tenant
      self.rcfile = rcfile
      self.err_strings=['Unable','Conflict','Bad Request','Error', 'Unknown',
			'Exception','Invalid','read-only','not supported',
			'prefix greater than subnet mask']
      
    def exe_command(self,cmdList):
      """
      Execute system calls
      """
      return run_openstack_cli(cmdList,self.cntrlrip,
                               username=self.uname,passwd=self.passwd)

    def gbp_uuid_get(self,cmd_out):
        '''
        Extracts UUID of a gbp object
        '''
        match=re.search("\\bid\\b\s+\| (.*) \|",cmd_out,re.I)
        if match != None:
           obj_uuid = match.group(1)
           #_log.info( "UUID:\n%s " %(obj_uuid))
           return obj_uuid.rstrip()
        else:
            return 0

    def gbp_action_config(self,cmd_val,name_uuid,tenant='',**kwargs):
	"""
        -- cmd_val== 0:delete; 1:create; 2:update
	-- name_uuid == UUID or name_string
        Create/Update/Delete Policy Action
        Returns assigned UUID on Create
        kwargs addresses the need for passing required/optional params
        """
        if not tenant:
           tenant = self.tenant
        if cmd_val == '' or name_uuid == '':
           _log.info('''Function Usage: gbp_action_config 0 "abc"\n
                      --cmd_val == 0:delete; 1:create; 2:update\n
                       -- name_uuid == UUID or name_string\n''')
           return 0
        #Build the command with mandatory param 'name_uuid' 
        cmd_tnt = 'gbp --os-tenant-name %s ' %(tenant)
        if cmd_val == 0:
           cmd = cmd_tnt+'policy-action-delete '+str(name_uuid)
        if cmd_val == 1:
           cmd = cmd_tnt+'policy-action-create '+str(name_uuid)
        if cmd_val == 2:
           cmd = cmd_tnt+'policy-action-update '+str(name_uuid)
        # Build the cmd string for optional/non-default args/values
        for arg, value in kwargs.items():
          cmd = cmd + " --" + "".join( '%s %s' %(arg, value ))
        # Execute the policy-action-config-cmd
        cmd_out = self.exe_command(cmd)
        if cmd_out:
            if cmd_val==1:
               action_uuid = self.gbp_uuid_get(cmd_out)
               return action_uuid
        else:
            _log.error(
            "Cli cmd execution for policy-action %s failed" %(name_uuid))
            return 0

    def gbp_classif_config(self,cmd_val,name_uuid,tenant='',**kwargs):
        """
        -- cmd_val== 0:delete; 1:create; 2:update
        -- classifier_name == UUID or name_string
        Create/Update/Delete Policy Classifier
        Returns assigned UUID on Create
        kwargs addresses the need for passing required/optional params
        """
        if not tenant:
           tenant = self.tenant
        if cmd_val == '' or name_uuid == '':
           _log.info('''Function Usage: gbp_classifier_config 0 "abc"\n
                      --cmd_val == 0:delete; 1:create; 2:update\n
                      --name_uuid == UUID or name_string\n''')
           return 0
        #Build the command with mandatory param 'classifier_name'
        cmd_tnt = 'gbp --os-tenant-name %s ' %(tenant)
        if cmd_val == 0:
           cmd = cmd_tnt+'policy-classifier-delete '+str(name_uuid)
        if cmd_val == 1:
           cmd = cmd_tnt+'policy-classifier-create '+str(name_uuid)
        if cmd_val == 2:
           cmd = cmd_tnt+'policy-classifier-update '+str(name_uuid)
        # Build the cmd string for optional/non-default args/values
        for arg, value in kwargs.items():
          cmd = cmd + " --" + "".join( '%s %s' %(arg, value ))
        # Execute the policy-classifier-config-cmd
        cmd_out = self.exe_command(cmd)
	if cmd_out:
            if cmd_val==1:
               classifier_uuid = self.gbp_uuid_get(cmd_out)
               return classifier_uuid
        else:
            _log.error(
            "Cli cmd execution for policy-classifier %s failed" %(name_uuid))
            return 0

    def gbp_policy_cfg_all(self,cmd_val,cfgobj,name_uuid,tenant='',**kwargs):
        """
	--cfgobj== policy-*(where *=action;classifer,rule,ruleset,targetgroup,target
        --cmd_val== 0:delete; 1:create; 2:update
        --name_uuid == UUID or name_string
        Create/Update/Delete Policy Object
        Returns assigned UUID on Create
        kwargs addresses the need for passing required/optional params
        """
        if not tenant:
           tenant = self.tenant
        cfgobj_dict={"action":"policy-action","classifier":"policy-classifier","rule":"policy-rule",
                      "ruleset":"policy-rule-set","group":"policy-target-group","target":"policy-target",
                      "l2p":"l2policy","l3p":"l3policy","nsp":"network-service-policy",
                      "extseg":"external-segment","extpol":"external-policy","natpool":"nat-pool"}
        if cfgobj != '':
           if cfgobj not in cfgobj_dict:
              raise KeyError 
        if cmd_val == '' or name_uuid == '':
           _log.info('''Function Usage: gbp_policy_cfg_all 'rule' 0 "abc"\n
                      --cmd_val == 0:delete; 1:create; 2:update\n
                      -- name_uuid == UUID or name_string\n''')
           return 0
        #Build the command with mandatory params
        cmd_tnt = 'gbp --os-tenant-name %s ' %(tenant)
        if cmd_val == 0:
           cmd = cmd_tnt+'%s-delete ' % cfgobj_dict[cfgobj]+str(name_uuid)
        if cmd_val == 1:
           cmd = cmd_tnt+'%s-create ' % cfgobj_dict[cfgobj]+str(name_uuid)
        if cmd_val == 2:
           cmd = cmd_tnt+'%s-update ' % cfgobj_dict[cfgobj]+str(name_uuid)
        # Build the cmd string for optional/non-default args/values
        for arg, value in kwargs.items():
          if '_' in arg:
             arg=string.replace(arg,'_','-')
          cmd = cmd + " --" + "".join( '%s=%s' %(arg, value ))
        # Execute the cmd
        cmd_out = self.exe_command(cmd)
        if cmd_out:
            # If try clause succeeds for "create" cmd then parse the cmd_out to extract the UUID of the object
            try:
	        if cmd_val==1 and cfgobj=="group":
           	    obj_uuid = self.gbp_uuid_get(cmd_out)
           	    match = re.search(
                            "\\bl2_policy_id\\b\s+\| (.*) \|",cmd_out,re.I)
                    l2pid = match.group(1)
                    match = re.search(
                            "\\bsubnets\\b\s+\| (.*) \|",cmd_out,re.I)
                    subnetid = match.group(1)
                    return obj_uuid,l2pid.rstrip(),subnetid.rstrip()
       		if cmd_val==1 and cfgobj=="target":
           	    obj_uuid = self.gbp_uuid_get(cmd_out)
            	    match = re.search(
                            "\\bport_id\\b\s+\| (.*) \|",cmd_out,re.I)
           	    neutr_port_id = match.group(1)
           	    return obj_uuid.rstrip(),neutr_port_id.rstrip()
         	if cmd_val==1 and cfgobj=="l2p":
            	    obj_uuid = self.gbp_uuid_get(cmd_out)
            	    match = re.search(
                            "\\bl3_policy_id\\b\s+\| (.*) \|",cmd_out,re.I)
            	    l3p_uuid = match.group(1)
            	    return obj_uuid.rstrip(),l3p_uuid.rstrip()
         	if cmd_val==1 and cfgobj=="extseg":
            	    obj_uuid = self.gbp_uuid_get(cmd_out)
            	    match = re.search("\\bsubnet_id\\b\s+\| (.*) \|",cmd_out,re.I)
            	    subnet_uuid = match.group(1)
            	    return obj_uuid.rstrip(),subnet_uuid.rstrip()
         	if cmd_val==1:
           	    obj_uuid = self.gbp_uuid_get(cmd_out)
           	    return obj_uuid.rstrip()
            except Exception as e:
               exc_type, exc_value, exc_traceback = sys.exc_info()
               _log.info(
               'Exception Type = %s, Exception Object = %s'\
               %(exc_type,exc_traceback))
               return 0
            return 1
        else:
            _log.info(
            "Cli cmd execution failed for %s" %(cfgobj_dict[cfgobj]))
	    return 0

    def gbp_policy_cfg_upd_all(self,cfgobj,name_uuid,attr,tenant=''):
        """
        --cfgobj== policy-*(where *=action;classifer,rule,ruleset,targetgroup,target
        --name_uuid == UUID or name_string
        --attr == MUST be a dict, where key: attribute_name, while val: attribute's value(new value to update)
        Updates Policy Objects' editable attributes
        """
        if not tenant:
           tenant = self.tenant
        cfgobj_dict={"action":"policy-action","classifier":"policy-classifier","rule":"policy-rule",
                      "ruleset":"policy-rule-set","group":"policy-target-group","target":"policy-target",
                      "l2p":"l2policy","l3p":"l3policy","nsp":"network-service-policy"}
        if cfgobj != '':
           if cfgobj not in cfgobj_dict:
              raise KeyError
        if name_uuid == '' or not isinstance(attr,dict):
           _log.info('''Function Usage: gbp_policy_cfg_upd_all 'rule' "abc" {attr:attr_val}\n
                      --cmd_val == 0:delete; 1:create; 2:update\n
                      -- name_uuid == UUID or name_string\n''')
           return 0
        #Build the command with mandatory params
        cmd_tnt = 'gbp --os-tenant-name %s ' %(tenant)
        cmd = cmd_tnt+'%s-update ' % cfgobj_dict[cfgobj]+str(name_uuid)
        # Build the cmd string for optional/non-default args/values
        for arg, value in attr.iteritems():
          if '_' in arg:
             arg=string.replace(arg,'_','-')
          cmd = cmd + " --" + "".join( '%s %s' %(arg, value ))
        # Execute the update cmd
        cmd_out = self.exe_command(cmd)
	if not cmd_out:
            return 0
        else:
            return 1

    def gbp_del_all_anyobj(self,cfgobj,tenant=''):
        """
        This function deletes all entries for any policy-object
        """
        if not tenant:
           tenant =self.tenant
        cfgobj_dict={"action":"policy-action","classifier":"policy-classifier","rule":"policy-rule",
                      "ruleset":"policy-rule-set","group":"group","target":"policy-target",
                      "l2p":"l2policy","l3p":"l3policy","nsp":"network-service-policy",
                      "node":"servicechain-node","spec":"servicechain-spec"}
        if cfgobj != '':
           if cfgobj not in cfgobj_dict:
              raise KeyError
        #Build the command with mandatory params
        cmd_tnt = 'gbp --os-tenant-name %s ' %(tenant)
        cmd = cmd_tnt+'%s-list -c id ' % cfgobj_dict[cfgobj]
        cmd_out = self.exe_command(cmd)
        _out=cmd_out.split('\n')
        final_out = _out[3:len(_out)-1]
        _log.info("\nThe Policy Object %s to be deleted = \n%s" %(cfgobj_dict[cfgobj],cmd_out))
        for item in final_out:
            item = item.strip(' |')
            cmd = cmd_tnt+'%s-delete ' % cfgobj_dict[cfgobj]+str(item)
            cmd_out = self.exe_command(cmd)
        return 1 

    def get_netns(self,net_node_ip,subnet):
        """
        Returns the Network Node's Ntk NameSpace
        Associated with every VM
        """
        env.host_string = net_node_ip
        env.user = 'root'
        env.password = 'noir0123'
        
        if isinstance(subnet,list):
           netns_list = []
           with settings(warn_only=True):
              result = run("ip netns | grep qdhcp")
              out = [x.strip() for x in result.split('\n')]
              for netns in out:
                  cmd = "ip netns exec %s ifconfig" %(netns)
                  result = run(cmd).replace('\r\n',' ')
                  if result.find(subnet) > -1:
                     netns_list.append(netns)
           return netns_list
        else:
          with settings(warn_only=True):
           result = run("ip netns | grep qdhcp")
           out = [x.strip() for x in result.split('\n')]
           for netns in out:
                  cmd = "ip netns exec %s ifconfig" %(netns)
                  result = run(cmd).replace('\r\n',' ')
                  if result.find(subnet) > -1:
                     break
          return netns

    def get_vm_subnet(self,vm_string,ret=''):
        """
        ret = 'ip' : for returning VM-Port's IP
              'subnet' : for returning VM-Port's subnet
              '' : returns a list['ip,'subnet']
        """
        cmd = "nova list | grep %s" %(vm_string)
        out_put = self.exe_command(cmd)
        ip_match = re.search('.*=(\d+.\d+.\d+.\d+)',out_put,re.I)
        subn_match = re.search('.*=(\d+.\d+.\d+)',out_put,re.I)
        if ip_match != None and subn_match != None:
           if  ret == 'ip':
               return ip_match.group(1)
           elif ret == 'subnet':
               return subn_match.group(1)
           else:
               return [ip_match.group(1),subn_match.group(1)]
        else:
           return 0


