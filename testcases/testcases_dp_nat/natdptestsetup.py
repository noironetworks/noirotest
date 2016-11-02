#!/usr/bin/python

import sys
import logging
import os
import datetime
import yaml
from commands import *
from time import sleep
from libs.gbp_heat_libs import gbpHeat
from libs.gbp_nova_libs import gbpNova
from libs.gbp_aci_libs import GbpApic
from libs.gbp_compute import Compute
from libs.gbp_crud_libs import GBPCrud
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

    def __init__(self, cfg_file,preexist):
        """
        Iniatizing the test-cfg variables & classes
        """
        with open(cfg_file, 'rt') as f:
            conf = yaml.load(f)
        #self.preexist = conf['preexist'] #TBD: For now fed from commandline
	self.apicsystemID = conf['apic_system_id']
        self.nova_agg = conf['nova_agg_name']
        self.nova_az = conf['nova_az_name']
        self.az_node = conf['az_comp_node']
        self.ntk_node = conf['ntk_node']
	self.comp_node = conf['compute_2']
        self.cntlr_ip = conf['controller_ip']
        self.extgw = conf['ext_gw_rtr']
        self.apic_ip = conf['apic_ip']
        self.leaf1_ip = conf['leaf1_ip']
        self.leaf2_ip = conf['leaf2_ip']
        self.spine_ip = conf['spine_ip']
        if preexist:
            self.dnat_heat_temp = conf['preexist_dnat_temp']
        else:
            self.dnat_heat_temp = conf['dnat_heat_temp']
        #SNAT: Prexisting L3Out in Common, Ext-Seg being tenant-specific
        #will result in tenant-specific NAT-EPG where SNAT EPs will get
        #learned. Apparently thats will cause inconsistency and we should
        #not support such config. Discussed with Amit 
        self.snat_heat_temp = conf['snat_heat_temp']
        self.num_hosts = conf['num_comp_nodes']
        self.heat_stack_name = conf['heat_dp_nat_stack_name']
        self.ips_of_extgw = [conf['fip1_of_extgw'],
                             conf['fip2_of_extgw'], self.extgw]
        self.routeforsnat = re.search(
        '\\b(\d+.\d+.\d+.)\d+' '',conf['fip2_of_extgw'], re.I).group(1)+'0/24'
        self.pausetodebug = conf['pausetodebug']
        self.neutronconffile = conf['neutronconffile']
        self.gbpnova = gbpNova(self.cntlr_ip)
        self.gbpheat = gbpHeat(self.cntlr_ip)
	self.gbpaci = GbpApic(self.apic_ip,
                              'gbp',
			      apicsystemID=self.apicsystemID)
        self.gbpcrud = GBPCrud(self.cntlr_ip)
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
	self.L3Outlist = ['Management-Out', 'Datacenter-Out']

    def setup(self, nat_type, do_config=0, pertntnatEpg=False):
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
                      self._log.warning(
                      "\nResidual Nova Agg exits, hence deleting it")
                      self.gbpnova.avail_zone('cli',
                                              'removehost',
                                               self.nova_agg,
                                               hostname=self.az_node)
                      self.gbpnova.avail_zone('cli', 'delete', self.nova_agg)
                   self._log.info(
                   "\nCreating Nova Host-Aggregate & its Availability-zone")
                   self.agg_id = self.gbpnova.avail_zone('api',
                                                         'create',
                                                          self.nova_agg,
                                                          avail_zone_name\
                                                          =self.nova_az)
               except Exception:
                   self._log.error(
                   "\n ABORTING THE TESTSUITE RUN,nova host aggregate creation Failed",\
                   exc_info=True)
                   sys.exit(1)
               self._log.info(" Agg %s" % (self.agg_id))
               try:
                 self._log.info("\nAdding Nova host to availability-zone")
                 self.gbpnova.avail_zone('api', 
                                         'addhost', 
                                         self.agg_id, 
                                         hostname=self.az_node)
               except Exception:
                     self._log.info(
                     "\n ABORTING THE TESTSUITE RUN, availability zone creation Failed")
                     self.gbpnova.avail_zone('cli',
                                             'delete',
                                              self.agg_id) # Cleanup Agg_ID
                     sys.exit(1)
            if nat_type == 'dnat':
                if pertntnatEpg:
                   pattern = 'per_tenant_nat_epg=True'
                   editneutronconf(self.cntlr_ip,
                                   self.neutronconffile,
                                   pattern)
            if nat_type == 'snat':
                # Adding host_pool_cidr to the both L3Outs
		sectionlist = ['apic_external_network:Management-Out',
                               'apic_external_network:Datacenter-Out']
                patvallist = [self.hostpoolcidrL3OutA,
                              self.hostpoolcidrL3OutB]
		pattern = 'host_pool_cidr'
                #Remove any exiting host_pool_cidr form neutron config
                editneutronconf(self.cntlr_ip,
                                self.neutronconffile,
                                pattern,
                                add=False)
	        for section,patval in zip(sectionlist,patvallist):
                    editneutronconf(self.cntlr_ip,
                                    self.neutronconffile,
				    '%s=%s' %(pattern,patval),
                                    section=section)
            # Invoking Heat Stack for building up the Openstack Config
            # Expecting if at all there is residual heat-stack it
            # should be of the same name as that of this DP Reg
            self._log.info("\nCheck and Delete Residual Heat Stack")
            if not self.gbpheat.cfg_all_cli(0, self.heat_stack_name):
               self._log.error(
               "\n ABORTING THE TESTSUITE RUN, Delete of Residual Heat-Stack Failed")
               self.cleanup() # Because residual stack-delete already failed above
               sys.exit(1)
            self._log.info(
            "\n Invoking Heat-Temp for Config creation of %s" % (nat_type.upper()))
            if self.gbpheat.cfg_all_cli(1, self.heat_stack_name, heat_temp=self.heat_temp_test) == 0:
               self._log.error(
               "\n ABORTING THE TESTSUITE RUN, Heat-Stack create of %s Failed" % (self.heat_stack_name))
               self.cleanup(nat_type='dnat')
               sys.exit(1)
            sleep(5)  # Sleep 5s assuming that all objects areated in APIC
            self._log.info(
            "\n ADDING SSH-Filter to Svc_epg created for every dhcp_agent")
            #create_add_filter(self.apic_ip, svc_epg_list)
            self.gbpaci.create_add_filter(self.L2plist)
        if nat_type == 'dnat':
                ### <Generate the dict comprising VM-name and its FIPs > ###
                self.fipsOftargetVMs = {}
                for vm in self.targetvm_list:
                    self.fipsOftargetVMs[vm] = \
                    self.gbpnova.get_any_vm_property(vm)[0][1:3]
                print 'FIPs of Target VMs == %s' % (self.fipsOftargetVMs)
                return self.fipsOftargetVMs

    def verifySetup(self,nat_type,pertntnatEpg=False):
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
	    self._log.info(
	    "\n Verify relations bw BDs and Regular EPGs association")
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
		       'Svc Epg %s NOT found in APIC' %(svcEpg))
	    #Verify the BDs in OperState of Regular EPGs
	    if [epg for epg,bd in self.EpgL2p.iteritems() \
                if bd != operEpgs[epg]['bdname'] \
		    or operEpgs[epg]['bdstate'] != 'formed']:
		    raise Exception(
			  'epg %s has Unresolved BD' %(epg))
            #Verify the BDs in Operstate of NAT-EPGs(pertntnatEpg)
            #Tenant-based NAT-EPG is created under either or
            #both of these two conditions:
            #1. if per_tenant_nat_epg=True (Sungard)
            #2. if ExtSeg is created in Openstack with shared=False
            extsegs=self.gbpcrud.get_gbp_external_segment_list(getdict=True)
            if not extsegs['Datacenter-Out']['shared'] or pertntnatEpg:
	        self._log.info(
	        "\n Verify relations bw NAT-BDs and Regular EPGs association")
                #When both shared and pertntnatEpg=False, then match string
                #will be NAT-epg-Datacenter
                if not pertntnatEpg:
                    match = 'NAT-epg-Datacenter'
                else:
                    match = 'NAT-epg-'
                match_count = 0
                for natepg in operEpgs.keys():
                   if match in natepg:
                       match_count += 1
                       if not 'NAT-bd' in operEpgs[natepg]['bdname'] \
                       or operEpgs[natepg]['bdstate'] != 'formed':
                           raise Exception(
                            'epg %s has Unresolved BD' %(epg))
                #If pertntnatEpg=True, then per L3Out there will be
                #one nat-Epg, since this testsuite has two L3Outs
                #match_count must be 2
                if pertntnatEpg and match_count < 2:
                    raise Exception('Inconsistent number of NAT-EPGs')
                if not match_count :
                    raise Exception(
                        'NAT-EPG for Datacenter-Out L3out NOT found')
                #The NAT-BD will be created as tenant-specific but its
                #vrf should resolve in common-tenant(Pre-existing case)
	        self._log.info(
	        "\n Verify relations bw NAT-BDs and their VRFs")
                operBDs = self.gbpaci.getBdOper('admin')
                bdcount = 0
                for bd in operBDs.keys():
                    if 'NAT-bd-' in bd:
                        bdcount += 1
                        if not 'tn-common' in operBDs[bd]['vrfdn'] \
                        or operBDs[bd]['vrfstate'] != 'formed':
                            raise Exception(
                                'Inconsistent VRF/VRF-state in NAT-BD'
                                 )
                if not bdcount:
                    raise Exception('NAT-BD not created in the tenant-admin')
	    #Verify the Shadow L3Outs
	    self._log.info(
		"\n Verify the Shadow L3Outs")
	    L3Outs = self.gbpaci.getL3Out('admin')
	    l3p1,l3p2 = self.L3plist
	    #Since we know there will be ONLY 4 ShdL3Outs
	    #for this test setup
	    str1 = '_%s_Shd-%s' %(self.apicsystemID,l3p1)
	    str2 = '_%s_Shd-%s' %(self.apicsystemID,l3p2)
	    L3p1 = '_%s_%s' %(self.apicsystemID,l3p1)
	    L3p2 = '_%s_%s' %(self.apicsystemID,l3p2)
	    ShdL3Out = [l3out for l3out in L3Outs.keys()\
		        if str1 in l3out or str2 in l3out]
	    if len(ShdL3Out) == 4:
	        for l3out in ShdL3Out:
	    	    if (L3Outs[l3out]['vrfname'] == L3p1 \
		        or L3Outs[l3out]['vrfname'] == L3p2):
			if L3Outs[l3out]['vrfstate'] != 'formed':
			    raise Exception(
			        'VRF not resolved for %s' %(l3out))
		    else:
			raise Exception(
			    'VRF is not associated to %s' %(l3out))
	    else:
		raise Exception('4 ShdL3Outs are NOT created')
	    #Verify SNAT EPs and DNAT FIPs
	    #Irrespective of pertntnatEpg, the SNAT EPs will
	    #be learned in NAT-EPG in Common
            
	    getNatEp = self.gbpaci.getEpgOper('common')
	    state = 'learned,vmm'
	    if getNatEp:
               if nat_type == 'snat':
	        self._log.info(
		"\n Verify L3Out EPs created and Learned for SNAT")
	        for node in [self.comp_node,self.ntk_node]:
		    comp = Compute(node)
	            for l3out in self.L3Outlist:
	                 intf,ip,psn,epg,vmname = \
	                 comp.getSNATEp(l3out)
			 if epg in getNatEp.keys():
			    if vmname in getNatEp[epg].keys():
				if ip != getNatEp[epg][vmname]['ip'] \
				   or getNatEp[epg][vmname]['status'] \
					!= state:
					raise Exception(
                                        'SNAT IP %s of SNAT-EP %s NOT learned' \
					%(ip,vmname))
		       	    else:
				raise Exception(
                                 'nat-Ep %s is NOT FOUND in Common Tnt APIC' \
                                 %(vmname))
			 else:
			    raise Exception(
			    'nat-Epg %s NOT FOUND in APIC' %(epg))
	       if nat_type == 'dnat':
	          self._log.info(
		  "\n Verify L3Out EPs NOT created for DNAT")
                  for node in [self.comp_node,self.ntk_node]:
                      comp = Compute(node)
                      for l3out in self.L3Outlist:
                          if comp.getSNATEp(l3out):
                              raise Exception(
                                    'In DNAT-Tests, SNAT-EPs are found')
	          self._log.info(
		  "\n Verify FIPs Learned in NAT-EPGs for DNAT")
		  if pertntnatEpg:
		     #getNatEp = self.gbpaci.getEpgOper('admin')
		     getNatEp = operEpgs
		  for vm,fip in self.fipsOftargetVMs.iteritems():
		  #Each vm has two fips, so type(fip)=list
		        for epg,val in getNatEp.iteritems():
                            if 'NAT-epg-' in epg:
	                        if vm in val.keys():
                                   if val[vm]['ip'] not in fip \
				      or state != val[vm]['status']:
				      raise Exception(
				   'FIP %s NOT learned in ACI'\
				   %(fip))
			        else:
                                    raise Exception(
                                     "VM %s NOT Learned in nat-epg %s" %(epg))  
	    else:
		raise Exception(
		 'NAT-EPGs NOT found in Common Tenant of APIC')
	except Exception as e:
	    self._log.error(
                '\nSetup Verification Failed because of this issue: '+repr(e))
  	    return 0
	return 1

    def reloadAci(self,nodetype='borderleaf'):
        """
        Reload the leaf or Spine
        """
        if nodetype == 'borderleaf':
           self.gbpaci.reboot_aci(self.leaf1_ip)
        if nodetype == 'leaf':
           self.gbpaci.reboot_aci(self.leaf2_ip)
        if nodetype == 'spine':
           self.gbpaci.reboot_aci(self.spine_ip)
           
    def restartAgent(self):
        """
        Restart Agent OVS
        """
        for node in [self.ntk_node,self.comp_node]:
            state = action_service(node)
            if state:
               sleep(5)
               return 1
            else:
               return 0

    def cleanup(self,stack=0,avail=0,nat_type=''):
        # Need to call for instance delete if there is an instance
        self._log.info("Cleaning Up The Test Config")
        if not stack:
           if nat_type == 'dnat': #Reason: heat-stack errors out on NSP/NAT-Pool dependency
               vmlist = ['App-Server', 'Web-Server', 'Web-Client-1', 'Web-Client-2']
               for vm in vmlist:
                   self.gbpnova.vm_delete(vm)
               self._log.info("\nStep: Blind CleanUp: Release FIPs")
               self.gbpnova.delete_release_fips()
               self._log.info("\nStep: Blind CleanUp: Delete PTs")
               pt_list = self.gbpcrud.get_gbp_policy_target_list()
               if len(pt_list) > 0:
                  for pt in pt_list:
                    self.gbpcrud.delete_gbp_policy_target(pt, property_type='uuid')
               self._log.info("\nStep: Blind CleanUp: Delete PTGs")
               ptg_list = self.gbpcrud.get_gbp_policy_target_group_list()
               if len(ptg_list) > 0:
                  for ptg in ptg_list:
                    self.gbpcrud.delete_gbp_policy_target_group(ptg, property_type='uuid')
               self._log.info("\nStep: Blind CleanUp: Delete NSPs")
               self.gbpcrud.delete_gbp_network_service_policy()
           self.gbpheat.cfg_all_cli(0, self.heat_stack_name)
           # Ntk namespace cleanup in Network-Node.. VM names are static
           # throughout the test-cycle
           del_netns(self.ntk_node)
        if not avail:
           self.gbpnova.avail_zone('cli',
                                   'removehost',
                                   self.nova_agg,
                                   hostname=self.az_node)
           self.gbpnova.avail_zone('cli', 'delete', self.nova_agg)
        #Remove the test-added config from neutron conf
        for pattern in ['host_pool_cidr',
                        'per_tenant_nat_epg',
                         ]:
            editneutronconf(self.cntlr_ip,
                            self.neutronconffile,
                            pattern,
                            add=False)
                                                                   
