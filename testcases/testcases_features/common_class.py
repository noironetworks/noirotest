#!/usr/bin/python

import logging
import re
import string
import sys
from commands import *
getoutput("rm -rf /tmp/test*") #Deletes pre-existing test logs 
from time import sleep
from libs.gbp_aci_libs import *
from libs.gbp_utils import *
from libs.neutron import *
from libs.gbp_compute import *
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_pexp_traff_libs import gbpExpTraff
from testcases.config import conf
from testcases.testcases_nat_func.traff_from_extgw import *

# Initialize logging
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
# create a logfile handler
hdlr = logging.FileHandler('/tmp/test_feature.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)
# Add the handler to the logger
LOG.addHandler(hdlr)

#Extract and set global vars from config file
#NOTE:The external-segment is hardcoded to 'Management-Out'
CNTRLIP = conf['controller_ip']
APICIP = conf['apic_ip']
TNT =  'BUCEPHALUS'
EXTRTR = conf['ext_rtr']
AVZONE = conf['nova_az_name']
AVHOST = conf['az_comp_node']
COMPUTE1 = conf['network_node']
COMPUTE2 = conf['compute-2']
pausetodebug = conf['pausetodebug']
APICVRF = "--apic:distinguished_names type=dict"+\
	  " VRF='uni/tn-common/ctx-DcExtVRF'"
ACT = 'ALLOW'
CLS_ICMP = 'ICMP'
CLS_TCP = 'TCP'
PR_ICMP = 'PR-ICMP'
PR_TCP = 'PR-TCP'
PRS_ICMP_TCP = 'CONT-ICMP-TCP'
PRS_ICMP = 'CONT-ICMP'
PRS_TCP = 'CONT-TCP'
comp = Compute(AVHOST)
neutron = neutronCli(CNTRLIP)
neutron_api = neutronPy(CNTRLIP,tenant=TNT)

#Create TNT
TNT_ID = neutron.addDelkeystoneTnt(TNT, 'create')
LOG.info("Tenant ID for Tenant %s = %s" %(TNT,TNT_ID))

class resource(object):

    def __init__(self, feature):
	self.feature = feature
	if feature == 'psec':
	    self.cidr = '14.14.14.0/24'
	if feature == 'aap':
	    self.cidr = '15.15.15.0/24'
	    self.vip = '15.15.15.20'
	if feature == 'useg':
	    self.cidr = '16.16.16.0/24'
	if feature == 'apg':
	    self.cidr = '17.17.17.0/24'
	self.net_name = '%s_net' %(feature.upper())
	self.sub_name = '%s_sub' %(feature.upper())
	self.vm1 = '%s_VM1' %(feature.upper())
	self.vm2 = '%s_VM2' %(feature.upper())
	    
    def create_network_subnet(self,repeat=False):
	try:
	    if repeat and self.feature == 'psec':
	        self.netID = neutron_api.create_net(self.net_name,port_security_enabled=False)
	    else:
	        self.netID = neutron_api.create_net(self.net_name)
	    self.subID = neutron_api.create_subnet(self.sub_name,
					    self.cidr,
					    self.netID)
        except Exception as e:
            LOG.error('Create Network/Subnet Failed: '+repr(e))
	    return 0
        return True

    def create_vm(self):
	self.vm_prop = {}
	if self.feature == 'aap':
            neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default icmp -1 -1 0.0.0.0/0'
            % (TNT))
            neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default tcp 22 22 0.0.0.0/0'
            % (TNT))
            neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default tcp 80 80 0.0.0.0/0'
            % (TNT))
	for vmname in [self.vm1, self.vm2]:
	    try:
                vm = neutron.spawnVM(TNT,
                                 vmname,
                                 self.netID,
                                 availzone=AVZONE
                                 )
		self.vm_prop[vmname]={'ip' : vm[0], 'port_id' : vm[1], 'mac' : vm[2]}
	    except Exception as e:
                LOG.error('VM Creation for tnt %s Failed: ' %(TNT)+repr(e))
                return 0
	return True

    def update_port(self,enable=True):
	try:
	    if self.feature == 'psec':
		prop = {'port_security_enabled' : enable}
	    if self.feature == 'aap':
		if enable:
		    prop = {'allowed_address_pairs' :\
			 [{'ip_address' : self.vip}]}
	        else:
		    prop = {'allowed_address_pairs' : []}
	    if self.feature == 'psec':
		for vm in [self.vm1, self.vm2]:
		    port = self.vm_prop[self.vm1]['port_id']
		    if not enable:	
		        neutron_api.update_port(port,
					    port_prop={'security_groups' : []})
		    neutron_api.update_port(port, port_prop=prop)
	    if self.feature == 'aap':
		for vm in  [self.vm1, self.vm2]:
		    port = self.vm_prop[vm]['port_id']
		    neutron_api.update_port(port, port_prop=prop)
	except Exception as e:
	    LOG.error(
	    'Updating port-property %s for port %s Failed: ' %(prop,port)+repr(e))
	    return 0
	return True

    def create_aap_port(self):
	try:
	    neutron_api.create_port(self.netID,fixed_ips=self.vip)
	except Exception as e:
	    LOG.error('AAP port create failed: '+repr(e))
	    return 0

    def verify_port(self, value):
	try:
	    if self.feature == 'psec':
	        all_port_props = neutron_api.get_all_port_details(
					prop='port_security_enabled')
		for vm in [self.vm1, self.vm2]:
	            if all_port_props[self.vm_prop[vm]['port_id']]\
			['port_security_enabled'] != value or \
		all_port_props[self.vm_prop[vm]['port_id']]['status'] != \
		'ACTIVE':
	 	        raise Exception('Unexpected port property or value')
	    if self.feature == 'aap':
	        all_port_props = neutron_api.get_all_port_details()
		for vm in [self.vm1, self.vm2]:
	            if all_port_props[self.vm_prop[self.vm1]['port_id']]\
                      ['allowed_address_pairs'][0]['ip_address'] != value or \
		all_port_props[self.vm_prop[self.vm1]['port_id']]['status'] !=\
		'ACTIVE':
	 	        raise Exception('Unexpected port property or value')
	except Exception as e:
	    LOG.error('Port verify failed: '+repr(e))
	    return 0
	return True

    def verify_ep(self,prop_value):
	    if self.feature == 'psec':
	        return comp.verify_EpFile(self.vm_prop[self.vm1]['port_id'],
				    self.vm_prop[self.vm1]['mac'],
				    promiscuous_mode = prop_value)
	    if self.feature == 'aap':
		for vm in  [self.vm1, self.vm2]:
	            result = comp.verify_EpFile(self.vm_prop[vm]['port_id'],
				    self.vm_prop[vm]['mac'],
				    virtual_ip = [{"ip" : prop_value,
						   "mac" : self.vm_prop[vm][mac]}]
				)
		    if not result:
			return False
		return True

    def cleanup(self,resourceOnly=False):
	#Delete VMs
        neutron.runcmd('nova --os-tenant-name %s delete %s %s' 
			%(TNT, self.vm1, self.vm2))
	#Purge Openstack/AIM resources
	neutron.purgeresource(TNT_ID,resourceOnly=resourceOnly)
