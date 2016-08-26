#!/usr/bin/python

import sys
import logging
import os
import datetime
import yaml
from commands import *
from time import sleep
from libs.gbp_heat_libs import Gbp_Heat
from libs.gbp_nova_libs import Gbp_Nova
from libs.gbp_aci_libs import GbpApic
from libs.gbp_utils import *


class nat_dp_main_config(object):
    """
    The intent of this class is to setup the complete GBP config 
    needed for running all DP testcases
    """
    # Initialize logging
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
    _log = logging.getLogger(__name__)
    hdlr = logging.FileHandler('/tmp/test_gbp_natdp_main_config.log')
    _log.setLevel(logging.INFO)
    _log.setLevel(logging.DEBUG)

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
        self.extgw = conf['ext_gw_rtr']
        self.apic_ip = conf['apic_ip']
        self.dnat_heat_temp = conf['dnat_heat_temp']
        self.snat_heat_temp = conf['snat_heat_temp']
        self.num_hosts = conf['num_comp_nodes']
        self.heat_stack_name = conf['heat_dp_nat_stack_name']
        self.ips_of_extgw = [conf['fip1_of_extgw'],
                             conf['fip2_of_extgw'], self.extgw]
        self.pausetodebug = conf['pausetodebug']
        self.neutronconffile = conf['neutronconffile']
        self.gbpnova = Gbp_Nova(self.cntlr_ip)
        self.gbpheat = Gbp_Heat(self.cntlr_ip)
	self.gbpaci = GbpApic(self.apic_ip,
                              'gbp',
			      apicsystemID=self.apicsystemID)
        self.hostpoolcidrL3OutA = '50.50.50.1/24'
        self.hostpoolcidrL3OutB = '60.60.60.1/24'
	#Instead of defining the below static labels/vars
	#could have sourced the heat.yaml file and read it
	#But since this TestConfig defined in yaml file
	#WILL NOT change hence being lazy as a mule
	self.targetvm_list = ['Web-Server', 'Web-Client-1',
				'Web-Client-2', 'App-Server']
	self.L3plist = ['DCL3P1','DCL3P2']
	#Note: change the order of list will affect the below dict
	self.Epglist = ['APPPTG','WEBSRVRPTG','WEBCLNTPTG']
	self.L2plist = ['APPL2P','WEBSRVRL2P','WEBCLNTL2P']
	self.EpgL2p = dict(zip(self.Epglist,self.L2plist))

    def setup(self, nat_type, do_config=0):
        """
        Availability Zone creation
        Heat Stack Creates All Test Config
        Generate dict comprising VM-name and FIPs
        <do_config> : Added this do_config, just runner to fetch FIPs
                    without having to run the whole setup, assuming
                    that setup was run before and the VMs exist
        """
        # Enabling Route Reflector
        self._log.info("\n Set the APIC Route Reflector")
        cmd = 'apic-route-reflector --ssl --no-secure --apic-ip %s admin noir0123' % (self.apic_ip)
        getoutput(cmd)
        if nat_type == 'dnat':
            self.heat_temp_test = self.dnat_heat_temp
        else:
            self.heat_temp_test = self.snat_heat_temp
        if do_config == 0:
            self._log.info(
                "\n Updating Nova Quota")
            if self.gbpnova.quota_update() == 0:
                self._log.info(
                    "\n ABORTING THE TESTSUITE RUN, Updating the Nova Quota's Failed")
                sys.exit(1)
            if self.num_hosts > 1:
               try:
                   cmd = "nova aggregate-list" # Check if Agg already exists then delete
                   if self.nova_agg in getoutput(cmd):
                      self._log.warning("\nResidual Nova Agg exits, hence deleting it")
                      self.gbpnova.avail_zone('cli', 'removehost', self.nova_agg, hostname=self.comp_node)
                      self.gbpnova.avail_zone('cli', 'delete', self.nova_agg)
                   self._log.info("\nCreating Nova Host-Aggregate & its Availability-zone")
                   self.agg_id = self.gbpnova.avail_zone(
                        'api', 'create', self.nova_agg, avail_zone_name=self.nova_az)
               except Exception, e:
                   self._log.error(
                         "\n ABORTING THE TESTSUITE RUN,nova host aggregate creation Failed", exc_info=True)
                   sys.exit(1)
               self._log.info(" Agg %s" % (self.agg_id))
               try:
                 self._log.info("\nAdding Nova host to availability-zone")
                 self.gbpnova.avail_zone('api', 'addhost', self.agg_id, hostname=self.comp_node)
               except Exception, e:
                     self._log.info(
                        "\n ABORTING THE TESTSUITE RUN, availability zone creation Failed")
                     self.gbpnova.avail_zone(
                        'cli', 'delete', self.agg_id)  # Cleanup Agg_ID
                     sys.exit(1)
            if nat_type == 'snat':
                # Adding host_pool_cidr to the both L3Outs
                snataddhostpoolcidr(self.cntlr_ip,
                                    self.neutronconffile,
                                    'Management-Out',
				    self.hostpoolcidrL3OutA)
                snataddhostpoolcidr(self.cntlr_ip,
				    self.neutronconffile,
				    'Datacenter-Out',
				    self.hostpoolcidrL3OutB)
            # Invoking Heat Stack for building up the Openstack Config
            # Expecting if at all there is residual heat-stack it
            # should be of the same name as that of this DP Reg
            self._log.info("\nCheck and Delete Residual Heat Stack")
            if self.gbpheat.cfg_all_cli(0, self.heat_stack_name) != 1:
               self._log.error(
                   "\n ABORTING THE TESTSUITE RUN, Delete of Residual Heat-Stack Failed")
               self.cleanup(stack=1) # Because residual stack-delete already failed above
               sys.exit(1)
            self._log.info(
                "\n Invoking Heat-Temp for Config creation of %s" % (nat_type.upper()))
            if self.gbpheat.cfg_all_cli(1, self.heat_stack_name, heat_temp=self.heat_temp_test) == 0:
               self._log.error(
                    "\n ABORTING THE TESTSUITE RUN, Heat-Stack create of %s Failed" % (self.heat_stack_name))
               self.cleanup()
               sys.exit(1)
            sleep(5)  # Sleep 5s assuming that all objects areated in APIC
            self._log.info(
                "\n ADDING SSH-Filter to Svc_epg created for every dhcp_agent")
            #create_add_filter(self.apic_ip, svc_epg_list)
            self.gbpaci.create_add_filter(self.L2plist)
        ### <Generate the dict comprising VM-name and its FIPs > ###
        self.fipsOftargetVMs = {}
        for vm in self.targetvm_list:
                self.fipsOftargetVMs[vm] = self.gbpnova.get_any_vm_property(vm)[
                    0][1:3]
        if nat_type == 'dnat':
               print 'FIPs of Target VMs == %s' % (self.fipsOftargetVMs)
               return self.fipsOftargetVMs

    def verifySetup(self):
	"""
	Verifies the Setup after being brought up
	"""
	self._log.info(
	    "\nVerify the Orchestrated Configuration in ACI")
	try:
	    self._log.info(
		"\n Verify the Operatonal State of EPGs")
	    operEpgs = self.gbpaci.getEpgOper('admin')
	    if operEpgs:
		vmstate = 'learned,vmm'
		for vm in self.targetvm_list:
		    notfound = 0
		    for epg,value in operEpgs.iteritems():
			if vm in value['vm']:
		           if not state in value['status']:
			       raise VerifyError(
                                 'vm %s NOT Learned in Epg %s' %(vm,epg)
				 )
			else:
			    notfound += 1
		    if notfound == len(operEpgs):
			raise VerifyError(
			  'vm %s NOT found in APIC' %(vm))
	    if [epg for epg,bd in operEpgs.iteritems() \
                if bd['bdname'] != self.EpgL2p[epg] \
		    or bd['bdstate'] != 'formed']:
		    raise VerifyError(
			  'epg %s has Unresolved BD' %(epg))
	    self._log.info(
		"\n Verify the Shadow L3Outs")
	    L3Outs = self.gbpaci.getL3Out('admin')
	    l3p1,l3p2 = self.L3plist
	    #Since we know there will be ONLY 4 ShdL3Outs
	    #for this test setup
	    str1 = '_%s_Shd-%s' %(self.apicsystemID,l3p1)
	    str2 = '_%s_Shd-%s' %(self.apicsystemID,l3p2)
	    ShdL3Out = [l3out for l3out in L3Outs.keys()\
		        if str1 in key or str2 in key]
	    if len(ShdL3Out) == 4:
	        for l3out in ShdL3Out:
	    	    if (L3Outs[l3out]['vrfname'] == l3p1 \
		        or L3Outs[l3out]['vrfname'] == l3p2):
			if L3Outs[l3out]['vrfstate'] != 'formed':
			    raise VerifyError(
			        'VRF not resolved for %s' %(l3out))
		    else:
			raise VerifyError(
			    'VRF is not associated to %s' %(l3out))
	    else:
		raise VerifyError('4 ShdL3Outs are NOT created')
	except Exception as e:
	    self._log.error(
                '\nSetup Verification Failed because of this issue'+repr(e))
  	    return 0
	finally:
	    return 1
	# NAT EPs(FIPs and SNAT)
	# Fetch SNAT EP from Comp

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
                                                                   
