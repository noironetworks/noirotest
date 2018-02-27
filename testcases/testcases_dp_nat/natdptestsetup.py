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
from libs.gbp_aci_libs import gbpApic
from libs.gbp_compute import Compute
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_utils import *
from testcases.config import conf

# Initialize logging
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
# create a logfile handler
hdlr = logging.FileHandler('/tmp/testsuite_dp_nat.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)
# Add the handler to the logger
LOG.addHandler(hdlr)

apicsystemID = conf['apic_system_id']
nova_agg = conf['nova_agg_name']
nova_az = conf['nova_az_name']
az_node = conf['az_comp_node']
network_node = conf['network_node']
comp_node = conf['compute-2']
cntlr_ip = conf['controller_ip']
extgw = conf['ext_rtr']
priL3Out = conf['primary_L3out']
secL3Out = conf['secondary_L3out']
priL3OutNet=conf.get('primary_L3out_net')
secL3OutNet=conf.get('secondary_L3out_net')
apic_ip = conf['apic_ip']
leaf1_ip = conf['leaf1_ip']
leaf2_ip = conf['leaf2_ip']
spine_ip = conf['spine_ip']
plugin = conf['plugin-type']
if plugin:
    from libs.neutron import *
    neutron = neutronCli(cntlr_ip)
dnat_heat_temp = conf['preexist_dnat_temp']
dnat_heat_temp = conf['dnat_heat_temp']
#SNAT: Prexisting L3Out in Common, Ext-Seg being tenant-specific
#will result in tenant-specific NAT-EPG where SNAT EPs will get
#learned. Apparently thats will cause inconsistency and we should
#not support such config. Discussed with Amit 
snat_heat_temp = conf['snat_heat_temp']
num_hosts = conf['num_comp_nodes']
heat_stack_name = conf['heat_dp_nat_stack_name']
ips_of_extgw = [conf['extrtr_ip1'],
                conf['extrtr_ip2'], extgw]
routefordest = re.search(
       '\\b(\d+.\d+.\d+.)\d+' '',conf['extrtr_ip2'], re.I).group(1)+'0/24'
pausetodebug = conf['pausetodebug']
neutronconffile = conf['neutronconffile']
gbpnova = gbpNova(cntlr_ip)
gbpheat = gbpHeat(cntlr_ip)
gbpaci = gbpApic(apic_ip, apicsystemID=apicsystemID)
gbpcrud = GBPCrud(cntlr_ip)
hostpoolcidrL3OutA = '55.55.55.1/24'
hostpoolcidrL3OutB = '66.66.66.1/24'
#Instead of defining the below static labels/vars
#could have sourced the heat.yaml file and read it
#But since this TestConfig defined in yaml file
#WILL NOT change hence being lazy as a mule
targetvm_list = ['Web-Server', 'Web-Client-1',
		'Web-Client-2', 'App-Server']
L3plist = ['DCL3P1','DCL3P2']
#Note: change the order of list will affect the below dict
Epglist = ['APPPTG','WEBSRVRPTG','WEBCLNTPTG']
L2plist = ['APPL2P','WEBSRVRL2P','WEBCLNTL2P']
EpgL2p = dict(zip(Epglist,L2plist))
L3Outlist = [priL3Out, secL3Out]

class nat_dp_main_config(object):
    """
    The intent of this class is to setup the complete GBP config 
    needed for running all DP testcases
    """

    def create_external_networks(self):
            LOG.info(
            "\n## Create External Networks for L3Outs:: %s & %s ##" %(priL3Out, secL3Out))
            try:
                aimntkcfg_primary = '--apic:distinguished_names type=dict'+\
                 ' ExternalNetwork='+\
                 'uni/tn-common/out-%s/instP-MgmtExtPol' %(priL3Out)
                 'uni/tn-common/out-%(l3out)s/instP-%(l3pol)s' % {
                 'l3out': priL3Out, 'l3pol': priL3OutNet}
                aimsnat = '--apic:snat_host_pool True'
                neutron.netcrud(priL3Out,'create',external=True,
                            shared=True, aim = aimntkcfg_primary)
                self.EXTSUB1 = neutron.subnetcrud('extsub1','create',priL3Out,
                               cidr='50.50.50.0/24',extsub=True)
                self.EXTSUB3 = neutron.subnetcrud('extsub3','create',priL3Out,
                               cidr=hostpoolcidrL3OutA,extsub=True,aim=aimsnat)


                aimntkcfg_sec = '--apic:distinguished_names type=dict'+\
                 ' ExternalNetwork='+\
                 'uni/tn-common/out-%(l3out)s/instP-%(l3pol)s' % {
                 'l3out': secL3Out, 'l3pol': secL3OutNet}
                aimsnat = '--apic:snat_host_pool True'
                neutron.netcrud(secL3Out,'create',external=True,
                            shared=True, aim = aimntkcfg_sec)
                self.EXTSUB2 = neutron.subnetcrud('extsub2','create',secL3Out,
                               cidr='60.60.60.0/24',extsub=True)
                self.EXTSUB4 = neutron.subnetcrud('extsub4','create',secL3Out,
                               cidr=hostpoolcidrL3OutB,extsub=True,aim=aimsnat)
	    except Exception as e:
		LOG.ERROR("External Network Create Failed for MergedPlugin")
		for l3out in [priL3Out, secL3Out]:
	            neutron.runcmd('neutron net-delete %s' %(l3out))
	    	return 0
	    return 1

    def setup(self, nat_type, do_config=0, pertntnatEpg=False):
        """
        Heat Stack Creates All Test Config
        Generate dict comprising VM-name and FIPs
        <do_config> : Added this do_config, just runner to fetch FIPs
                    without having to run the whole setup, assuming
                    that setup was run before and the VMs exist
        """
        if nat_type == 'dnat':
            self.heat_temp_test = dnat_heat_temp
        else:
            self.heat_temp_test = snat_heat_temp
        if do_config == 0:
            if nat_type == 'dnat':
                if pertntnatEpg:
                   pattern = 'per_tenant_nat_epg=True'
                   editneutronconf(cntlr_ip,
                                   neutronconffile,
                                   pattern)
            if nat_type == 'snat':
		if not plugin:
                    # Adding host_pool_cidr to the both L3Outs
		    sec1 = 'apic_external_network:%s' % priL3Out
		    sec2 = 'apic_external_network:%s' % secL3Out
		    sectionlist = [sec1, sec2]
                    patvallist = [hostpoolcidrL3OutA,
                              hostpoolcidrL3OutB]
		    pattern = 'host_pool_cidr'
                    #Remove any exiting host_pool_cidr form neutron config
                    editneutronconf(cntlr_ip,
                                neutronconffile,
                                pattern,
                                add=False)
	            for section,patval in zip(sectionlist,patvallist):
                        editneutronconf(cntlr_ip,
                                    neutronconffile,
				    '%s=%s' %(pattern,patval),
                                    section=section)
            # Invoking Heat Stack for building up the Openstack Config
            # Expecting if at all there is residual heat-stack it
            # should be of the same name as that of this DP Reg
            LOG.info("\nCheck and Delete Residual Heat Stack")
            if not gbpheat.cfg_all_cli(0, heat_stack_name):
               LOG.error(
               "\n ABORTING THE TESTSUITE RUN, Delete of Residual Heat-Stack Failed")
               self.cleanup() # Because residual stack-delete already failed above
               sys.exit(1)
	    if plugin:
		self.create_external_networks()
            LOG.info(
            "\n Invoking Heat-Temp for Config creation of %s" % (nat_type.upper()))
            if gbpheat.cfg_all_cli(1, heat_stack_name, heat_temp=self.heat_temp_test) == 0:
               LOG.error(
               "\n ABORTING THE TESTSUITE RUN, Heat-Stack create of %s Failed" % (heat_stack_name))
               self.cleanup(nat_type='dnat')
               sys.exit(1)
            sleep(5)  # Sleep 5s assuming that all objects areated in APIC
	    if not plugin:
                LOG.info(
                "\n ADDING SSH-Filter to Svc_epg created for every dhcp_agent")
                #create_add_filter(apic_ip, svc_epg_list)
                gbpaci.create_add_filter('admin')
        if nat_type == 'dnat':
                ### <Generate the dict comprising VM-name and its FIPs > ###
                self.fipsOftargetVMs = {}
                for vm in targetvm_list:
                    self.fipsOftargetVMs[vm] = \
                    gbpnova.get_any_vm_property(vm)[0][1:3]
                print 'FIPs of Target VMs == %s' % (self.fipsOftargetVMs)
                return self.fipsOftargetVMs

    def verifySetup(self,nat_type,pertntnatEpg=False):
	"""
	Verifies the Setup after being brought up
	"""
	LOG.info(
	    "\nVerify the Orchestrated Configuration in ACI")
	try:
	    LOG.info(
		"\n Verify the Operatonal State of EPGs")
	    operEpgs = gbpaci.getEpgOper('admin')
	    if operEpgs:
		vmstate = 'learned,vmm'
		for vm in targetvm_list:
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
	    LOG.info(
	    "\n Verify relations bw BDs and Regular EPGs association")
            #Verify the BDs in OperState of Service EPGs
            #pop them out of the operEpgs
            for bd in L2plist:
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
	    if [epg for epg,bd in EpgL2p.iteritems() \
                if bd != operEpgs[epg]['bdname'] \
		    or operEpgs[epg]['bdstate'] != 'formed']:
		    raise Exception(
			  'epg %s has Unresolved BD' %(epg))
            #Verify the BDs in Operstate of NAT-EPGs(pertntnatEpg)
            #Tenant-based NAT-EPG is created under either or
            #both of these two conditions:
            #1. if per_tenant_nat_epg=True (Sungard)
            #2. if ExtSeg is created in Openstack with shared=False
            extsegs=gbpcrud.get_gbp_external_segment_list(getdict=True)
            if not extsegs[secL3Out]['shared'] or pertntnatEpg:
	        LOG.info(
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
                        'NAT-EPG for %s L3out NOT found' % secL3Out)
                #The NAT-BD will be created as tenant-specific but its
                #vrf should resolve in common-tenant(Pre-existing case)
	        LOG.info(
	        "\n Verify relations bw NAT-BDs and their VRFs")
                operBDs = gbpaci.getBdOper('admin')
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
	    LOG.info(
		"\n Verify the Shadow L3Outs")
	    L3Outs = gbpaci.getL3Out('admin')
	    l3p1,l3p2 = L3plist
	    #Since we know there will be ONLY 4 ShdL3Outs
	    #for this test setup
	    str1 = '_%s_Shd-%s' %(apicsystemID,l3p1)
	    str2 = '_%s_Shd-%s' %(apicsystemID,l3p2)
	    L3p1 = '_%s_%s' %(apicsystemID,l3p1)
	    L3p2 = '_%s_%s' %(apicsystemID,l3p2)
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
            
	    getNatEp = gbpaci.getEpgOper('common')
	    state = 'learned,vmm'
	    if getNatEp:
               if nat_type == 'snat':
	        LOG.info(
		"\n Verify L3Out EPs created and Learned for SNAT")
	        for node in [comp_node,network_node]:
		    comp = Compute(node)
	            for l3out in L3Outlist:
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
	          LOG.info(
		  "\n Verify L3Out EPs NOT created for DNAT")
                  for node in [comp_node,network_node]:
                      comp = Compute(node)
                      for l3out in L3Outlist:
                          if comp.getSNATEp(l3out):
                              raise Exception(
                                    'In DNAT-Tests, SNAT-EPs are found')
	          LOG.info(
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
	    LOG.error(
                '\nSetup Verification Failed because of this issue: '+repr(e))
  	    return 0
	return 1

    def reloadAci(self,nodetype='borderleaf'):
        """
        Reload the leaf or Spine
        """
        if nodetype == 'borderleaf':
           gbpaci.reboot_aci(leaf1_ip)
        if nodetype == 'leaf':
           gbpaci.reboot_aci(leaf2_ip)
        if nodetype == 'spine':
           gbpaci.reboot_aci(spine_ip)
           
    def restartAgent(self):
        """
        Restart Agent OVS
        """
        for node in [network_node,comp_node]:
            state = action_service(node)
            if state:
               sleep(5)
               return 1
            else:
               return 0

    def cleanup(self,stack=0,avail=0,nat_type=''):
        # Need to call for instance delete if there is an instance
        LOG.info("Cleaning Up The Test Config")
        if not stack:
           if nat_type == 'dnat': #Reason: heat-stack errors out on NSP/NAT-Pool dependency
               vmlist = ['App-Server', 'Web-Server', 'Web-Client-1', 'Web-Client-2']
               for vm in vmlist:
                   gbpnova.vm_delete(vm)
               LOG.info("\nStep: Blind CleanUp: Release FIPs")
               gbpnova.delete_release_fips()
               LOG.info("\nStep: Blind CleanUp: Delete PTs")
               pt_list = gbpcrud.get_gbp_policy_target_list()
               if len(pt_list) > 0:
                  for pt in pt_list:
                    gbpcrud.delete_gbp_policy_target(pt, property_type='uuid')
               LOG.info("\nStep: Blind CleanUp: Delete PTGs")
               ptg_list = gbpcrud.get_gbp_policy_target_group_list()
               if len(ptg_list) > 0:
                  for ptg in ptg_list:
                    gbpcrud.delete_gbp_policy_target_group(ptg, property_type='uuid')
               LOG.info("\nStep: Blind CleanUp: Delete NSPs")
               gbpcrud.delete_gbp_network_service_policy()
           gbpheat.cfg_all_cli(0, heat_stack_name)
           # Ntk namespace cleanup in Network-Node.. VM names are static
           # throughout the test-cycle
           del_netns(network_node)
        #Remove the test-added config from neutron conf
	if not plugin:
            for pattern in ['host_pool_cidr',
                        'per_tenant_nat_epg',
                         ]:
                editneutronconf(cntlr_ip,
                            neutronconffile,
                            pattern,
                            add=False)
	else:
            for l3out in [secL3out, priL3out]:
                neutron.runcmd('neutron net-delete %s' %(l3out))
                                                                   
