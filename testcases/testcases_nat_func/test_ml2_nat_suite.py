#!/usr/bin/python

import datetime
import logging
import pprint
import string
import sys
import yaml
from time import sleep
from libs.gbp_aci_libs import *
from libs.gbp_utils import *
from libs.neutron import *

# Initialize logging
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
# create a logfile handler
hdlr = logging.FileHandler('/tmp/test_ml2_nat.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)
# Add the handler to the logger
LOG.addHandler(hdlr)

def main():
    cfgfile = sys.argv[1]
    suite=NatML2TestSuite(cfgfile)
    suite.test_runner()

class NatML2TestSuite(object):
    
    def __init__(self,cfgfile):
        with open(cfgfile, 'rt') as f:
            conf = yaml.load(f)
        self.cntlrip = conf['controller_ip']
        self.apicip = conf['apic_ip']
	self.tenant_list = conf['tenant_list']
        self.extrtr = conf['ext_rtr']
        self.extrtr_ip1 = conf['extrtr_ip1']
        self.extrtr_ip2 = conf['extrtr_ip2']
        self.gwiplist = [self.extrtr_ip1, self.extrtr_ip2]
        self.ntknode = conf['network_node']
	self.neutron = neutronCli(self.cntlrip)
	self.apic = GbpApic(self.apicip,'ml2')
	self.tnt1,self.tnt2 = self.tenant_list[0],self.tenant_list[1]
	self.ntkNames = ['Net1','Net2','Net3']
	self.subNames = ['Sub1','Sub2','Sub3']
	self.apicsystemID = 'noirolab' #TODO: should auto fetch from neutron config
	self.Cidrs = {}
	self.Cidrs[self.tnt1] = ['2.2.2.0/28','3.3.3.0/28','4.4.4.0/28']
	self.Cidrs[self.tnt2] = ['7.7.7.0/28','8.8.8.0/28','9.9.9.0/28']
        
    def test_runner(self):
        """
        Method to run the Testcase in Ordered Steps
        """
	# Add Tenants
	LOG.info("\n Step:Common: Add Tenants and Users in Openstack")
	self.neutron.addDelkeystoneTnt(self.tenant_list,'create')
        # Initiate Global Configuration 
        test_results = {}
	# Add L3Out as Shared by 'Admin' Tenant
	LOG.info("\nStep:Common: Add L3Out=Management-Out as Shared by Admin Tenant")
	self.neutron.netcrud('Management-Out','create',external=True,shared=True)
        test_list = [self.test_vpr_nat_func_1]
        for test in test_list:
                if test() == 0:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'FAIL'
                    LOG.error("\n%s_%s == FAIL" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
                else:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'PASS'
                    LOG.info("\n%s_%s == PASS" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
        pprint.pprint(test_results)

    def verifyAciBDtoVRF(self,rtrid='shared'):
	unmatched = {}
	bdcheck = self.apic.getBdOper(self.tenant_list)
	for tnt in self.tenant_list:
	    unmatched[tnt] = []
	    if [unmatched[tnt].append(bdname) for bdname in self.ntkNames\
                if '_%s_%s' %(self.apicsystemID,rtrid) != bdcheck[tnt][bdname]['vrfname']\
                or bdcheck[tnt][bdname]['vrfstate'] != 'formed']:
                   return unmatched

    def test_vpr_nat_func_1(self):
        """
        Testcase-1 in VPR-NAT Workflow
        """
        LOG.info("\nExecution of Testcase TEST_VPR_NAT_FUNC_1 starts\n")

	LOG.info("\nStep-1:TC-1: Add Networks and Subnets for the tenants")
	subnetIDs = {}
	for tnt in self.tenant_list:
	    #Every Network has just one Subnet, 1:1
	    subnetIDs[tnt] = []
	    for index in range(len(self.ntkNames)):
	        netID = self.neutron.netcrud(self.ntkNames[index],'create',tnt)
	        subnetIDs[tnt].append(self.neutron.subnetcrud(self.subNames[index],
		                        'create',
			                ntkNameId=netID,
					cidr=self.Cidrs[tnt][index],
					tenant=tnt))

	LOG.info("\nStep-2:TC-1: Add Router for the tenants")
	rtrIDs = {}
	for tnt in self.tenant_list:
	    _id = self.neutron.rtrcrud('RTR1','create',tenant=tnt)    
	    rtrIDs[tnt]= _id
	LOG.info("\nRouter IDs for the respective Tenants == %s" %(rtrIDs))

	LOG.info("\nStep-3-TC-1:VerifyACI: VRF got created for this Router")
	vrfnotfound = []
	if [vrfnotfound.append(rtrIDs[tnt]) for tnt in self.tenant_list\
                if '_%s_%s' %(self.apicsystemID,rtrIDs[tnt])
		not in self.apic.getVrfs(tnt)[tnt]]:
	    LOG.info("\nStep-3-TC-1:Fail: Following VRFs not found in ACI = %" %(vrfnotfound))
            return 0    

	LOG.info("\nStep-4-TC-1:VerifyACI: BDs and their VRF resolves to *_shared")
	unmatchedvrfs = self.verifyAciBDtoVRF()
	if unmatchedvrfs:
	    LOG.error("\nStep-4-TC-1:Fail: Unresolved VRF for following BDs >> %s"
	              %(unmatchedvrfs))
	    return 0	     
	
	LOG.info("\nStep-5-TC-1: Add resp Router Interfaces to Tenants' networks")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(rtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetId) for subnetId in subnetIDs[tnt]]

        LOG.info("\nStep-6-TC-1: VerifyACI: Router's VRF resolves in the Tenant's BDs")
	unmatched = {}
	bdcheck = self.apic.getBdOper(self.tenant_list)
	for tnt in self.tenant_list:
	    unmatched[tnt] = []
	    if [unmatched[tnt].append(bdname) for bdname in self.ntkNames\
                if '_%s_%s' %(self.apicsystemID,rtrIDs[tnt]) != bdcheck[tnt][bdname]['vrfname']\
                or bdcheck[tnt][bdname]['vrfstate'] != 'formed']:
		    LOG.error("\nStep-6-TC-1:Fail:VRF %s did NOT resolve in Tenant %s following BD %s >>"
                              %(rtrIDs[tnt],tnt,unmatched))
                    return unmatched
	 

if __name__ == "__main__":
    main()
