#!/usr/bin/python

import sys
import logging
import os
import datetime
import yaml
from time import sleep
from commands import *
from libs.gbp_heat_libs import Gbp_Heat
from libs.gbp_nova_libs import Gbp_Nova
from libs.gbp_aci_libs import GbpApic
from libs.gbp_compute import Compute
from libs.gbp_utils import *


class gbp_main_config(object):
    """
    The intent of this class is to setup the complete GBP config 
    needed for running all DP testcases
    """

    # Initialize logging
    #logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.setLevel(logging.INFO)
    # create a logfile handler
    hdlr = logging.FileHandler('/tmp/test_gbp_dp_main_config.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    hdlr.setFormatter(formatter)
    # Add the handler to the logger
    _log.addHandler(hdlr)

    def __init__(self, cfg_file):
        """
        Iniatizing the test-cfg variables & classes
        """
        with open(cfg_file, 'rt') as f:
            conf = yaml.load(f)
	self.apicsystemID = conf['apic_system_id']
        self.nova_agg = conf['nova_agg_name']
        self.nova_az = conf['nova_az_name']
        self.comp_node = conf['az_comp_node']
        self.ntk_node = conf['ntk_node']
        self.cntlr_ip = conf['controller_ip']
        self.apic_ip = conf['apic_ip']
        self.apic_passwd = conf['apic_passwd']
        self.heat_temp_test = conf['main_setup_heat_temp']
        self.num_hosts = conf['num_comp_nodes']
        self.heat_stack_name = conf['heat_dp_stack_name']
	self.pausetodebug = conf['pausetodebug']
        self.test_parameters = conf['test_parameters']
        self.gbpnova = Gbp_Nova(self.cntlr_ip)
        self.gbpheat = Gbp_Heat(self.cntlr_ip)
	self.gbpaci = GbpApic(self.apic_ip,
			       'gbp',
			       apicsystemID=self.apicsystemID) 
	self.vmlist = ['VM1','VM2','VM3','VM4',
		       'VM5','VM6','VM7','VM8',
		       'VM9','VM10','VM11','VM12'	
		      ]
    def setup(self):
        """
        Availability Zone creation
        SSH Key creation
        Heat Stack Creates All Test Config
        """
        # Enabling Route Reflector
        self._log.info("\n Set the APIC Route Reflector")
        cmd = 'apic-route-reflector --ssl SSL %s admin noir0123' % (
            self.apic_ip)
        getoutput(cmd)

        # Updating/Enabling Nova config for quota & availability-zone
        self._log.info("\n Update Nova Quota")
        if self.gbpnova.quota_update() == 0:
            self._log.error(
                "\n ABORTING THE TESTSUITE RUN, Updating the Nova Quota's Failed")
            sys.exit(1)
        if self.num_hosts > 1:
            try:
               cmd = "nova aggregate-list" # Check if Agg already exists then delete
               if self.nova_agg in getoutput(cmd):
                  self._log.warning("Residual Nova Agg exits, hence deleting it")
                  self.gbpnova.avail_zone('cli', 'removehost', self.nova_agg, hostname=self.comp_node)
                  self.gbpnova.avail_zone('cli', 'delete', self.nova_agg)
               self._log.info("\nCreating Nova Host-aggregate & its Availability-zone")
               self.agg_id = self.gbpnova.avail_zone(
                       'api', 'create', self.nova_agg, avail_zone_name=self.nova_az)
            except Exception, e:
                self._log.error(
                    "\n ABORTING THE TESTSUITE RUN,nova host aggregate creation Failed", exc_info=True)
                sys.exit(1)
            self._log.info(" Agg %s" % (self.agg_id))
            try:
             self._log.info("\nAdding Nova host to availaibility-zone")
             self.gbpnova.avail_zone('api', 'addhost', self.agg_id, hostname=self.comp_node)
            except Exception, e:
                self._log.error(
                    "\n ABORTING THE TESTSUITE RUN, availability zone creation Failed", exc_info=True)
                self.gbpnova.avail_zone(
                    'cli', 'delete', self.agg_id)  # Cleanup Agg_ID
                sys.exit(1)

        # Invoking Heat Stack for building up the Openstack Config
        # Expecting if at all there is residual heat-stack it
        # should be of the same name as that of this DP Reg
        self._log.info("\nCheck and Delete Residual Heat Stack")
        if self.gbpheat.cfg_all_cli(0, self.heat_stack_name) != 1:
           self._log.error(
               "\n ABORTING THE TESTSUITE RUN, Delete of Residual Heat-Stack Failed") 
           self.cleanup(stack=1) # Because residual stack-delete already failed above
           sys.exit(1)
        self._log.info("\n Invoking Heat Stack for building config and VMs")
        if self.gbpheat.cfg_all_cli(1, self.heat_stack_name, heat_temp=self.heat_temp_test) == 0:
            self._log.error(
                "\n ABORTING THE TESTSUITE RUN, Heat-Stack create of %s Failed" % (self.heat_stack_name))
            self.cleanup()
            sys.exit(1)
        sleep(5)  # Sleep 5s assuming that all objects are created in APIC
        self._log.info(
            "\n Adding SSH-Filter to Svc_epg created for every dhcp_agent")
        self.L2plist = [
                        'demo_same_ptg_l2p_l3p_bd',
                        'demo_diff_ptg_same_l2p_l3p_bd',
                        'demo_diff_ptg_l2p_same_l3p_bd_1',
                        'demo_diff_ptg_l2p_same_l3p_bd_2',
                        'demo_srvr_bd', 'demo_clnt_bd'
                       ]
	if not self.gbpaci.create_add_filter(self.L2plist):
	    self._log.error(
            "\nABORTING THE TESTSUITE RUN,adding filter to SvcEpg failed")
	    self.cleanup()
	    sys.exit(1)

    def verifySetup(self):
   	"""
	Verfies the Setup after being brought up
	"""
	self._log.info(
	    "\nVerify the Orchestrated Configuration in ACI")
	try:
	    self._log.info(
		"\n Verify the Operatonal State of EPGs")
	    operEpgs = self.gbpaci.getEpgOper('admin')
	    if operEpgs:
		vmstate = 'learned,vmm'
		for vm in self.vmlist:
		    notfound = 0
		    for epg,value in operEpgs.iteritems():
			#since each value is a dict itself,
                        #with key = vmname
			if vm in value.keys():
		           if not vmstate in value[vm]['status']:
			       raise Exception(
                                 'vm %s NOT Learned in Epg %s' %(vm,epg)
				 )
		        else:
			    notfound += 1
		    if notfound == len(operEpgs.keys()):    
			raise Exception(
			     'vm %s NOT found in APIC' %(vm))
            #Verify the BDs in OperState of Service EPGs
            #pop them out of the operEpgs
            for bd in self.L2plist:
		svcEpg = 'Shd-%s' %(bd)
		if svcEpg in operEpgs.keys():
		    svcVal = operEpgs.pop(svcEpg)
		    if svcVal['bdname'] != bd \
			or svcVal['bdstate'] != 'formed':
			    raise Exception(
			    'epg %s has Unresolved BD' %(svcEpg))
		else:
		    raise Exception(
		       'SvcEpg %s NOT found in APIC' %(svcEpg))
	except Exception as e:
	    self._log.error(
            '\nSetup Verification Failed Because of this Issue: '+repr(e))
            self._log.error(
            "\nABORTING THE TESTSUITE RUN, on Setup Verification Failure")
	    if self.pausetodebug:
	       PauseToDebug()
  	    self.cleanup() # Calling cleanup on Verify Failure
            sys.exit(1)
	finally:
	    return 1

    def cleanup(self,stack=0,avail=0):
        # Need to call for instance delete if there is an instance
        self._log.info("Cleaning Up The Test Config")
        if stack == 0:
           self.gbpheat.cfg_all_cli(0, self.heat_stack_name)
           # Ntk namespace cleanup in Network-Node.. VM names are static
           # throughout the test-cycle
           del_netns(self.ntk_node)
        if avail == 0:
           self.gbpnova.avail_zone('cli', 'removehost',
                                   self.nova_agg, hostname=self.comp_node)
           self.gbpnova.avail_zone('cli', 'delete', self.nova_agg)
