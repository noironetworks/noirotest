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
        """
	# Add Tenants
	LOG.info("\n Step:Common: Add Tenants and Users in Openstack")
	self.neutron.addDelkeystoneTnt(self.tenant_list,'create')
        # Initiate Global Configuration 
        test_results = {}
	# Add L3Out as Shared by 'Admin' Tenant
	LOG.info("\nStep:Common: Add L3Out=Management-Out as Shared by Admin Tenant")
	self.neutron.netcrud('Management-Out','create',external=True,shared=True)
	"""
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
        LOG.info("\n########  Testcase TEST_VPR_NAT_FUNC_1   ###########\n"
		 "# Add Networks and Subnets for the tenants           #\n"
		 "# Add Router for each of the tenants 	               #\n"
		 "# VerifyACI: VRF created for each of this Router     #\n"
		 "# VerifyACI: BDs and their VRF resolves to *_shared  #\n"
		 "# Add resp Router Interfaces to Tenants' networks    #\n"
		 "# VerifyACI: Router's VRF resolves in the Tenant's BDs #\n"
		 "######################################################\n")
	LOG.info("\n Execution of Testcase starts #")

	LOG.info("\n# Step-1:TC-1: Add Networks and Subnets for the tenants #")
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

	LOG.info("\n# Step-2:TC-1: Add Router for the tenants #")
	rtrIDs = {}
	for tnt in self.tenant_list:
	    _id = self.neutron.rtrcrud('RTR1','create',tenant=tnt)    
	    rtrIDs[tnt]= _id
	LOG.info("\nRouter IDs for the respective Tenants == %s" %(rtrIDs))

	LOG.info("\n# Step-3-TC-1:VerifyACI: VRF got created for this Router #")
	vrfnotfound = []
	if [vrfnotfound.append(rtrIDs[tnt]) for tnt in self.tenant_list\
                if '_%s_%s' %(self.apicsystemID,rtrIDs[tnt])
		not in self.apic.getVrfs(tnt)[tnt]]:
	    LOG.info("\nStep-3-TC-1:Fail: Following VRFs not found in ACI = %" %(vrfnotfound))
            return 0    

	LOG.info("\n# Step-4-TC-1:VerifyACI: BDs and their VRF resolves to *_shared #")
	unmatchedvrfs = self.verifyAciBDtoVRF()
	if unmatchedvrfs:
	    LOG.error("\nStep-4-TC-1:Fail: Unresolved VRF for following BDs >> %s"
	              %(unmatchedvrfs))
	    return 0	     
	
	LOG.info("\n# Step-5-TC-1: Add resp Router Interfaces to Tenants' networks #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(rtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetId) for subnetId in subnetIDs[tnt]]

        LOG.info("\n# Step-6-TC-1: VerifyACI: Router's VRF resolves in the Tenant's BDs #")
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
	 

    def test_vpr_nat_func_2(self):
        """
        Testcase-2 in VPR-NAT Workflow
        """
        LOG.info("\n########  Testcase TEST_VPR_NAT_FUNC_2   ############\n"
		 "# Remove each tenant's Router from the attached ntks  #\n"
		 "# VerifyACI: VRF for each BD VRF resolves to *_shared #\n"
		 "# Add new subnet to the respective tenants's ntks     #\n"
		 "# Add back the Routers's interfaces to the above new subnets  #\n"
		 "# VerifyACI: Router's VRF resolves in the Tenant's BDs #\n"
		 "# Add back the Routers's interfaces to existing Old subnets of tenants'  #\n"
		 "# Verify: Routers' have interfaces attached to multiple subnets #\n"
		 "# Remove the router interface from all but one subnet in each ntk #\n"
		 "# VerifyACI: The BDs are STILL connected to Router's VRF #\n"
		 "#####################################################\n")
        LOG.info("\n Execution of Testcase starts #")

	LOG.info("\n# Step-1-TC-2: Remove each tenant's Router from the attached ntks #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(rtrIDs[tnt],'delete',rtrprop='interface',
			         subnet=subnetId) for subnetId in subnetIDs[tnt]]

	LOG.info("\n# Step-2-TC-2:VerifyACI: VRF for each BD VRF resolves to *_shared #")
	unmatchedvrfs = self.verifyAciBDtoVRF()
	if unmatchedvrfs:
	    LOG.error("\nStep-2-TC-2:Fail: Unresolved VRF for following BDs >> %s"
	              %(unmatchedvrfs))
	    return 0	     
	
	LOG.info("\n# Step-3-TC-2: Add new subnet to the respective tenants's ntks #")

	LOG.info("\n# Step-4-TC-2: Add back the Routers's interfaces to the above new subnets #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(rtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetId) for subnetId in subnetIDs[tnt]]

        LOG.info("\n# Step-5-TC-2: VerifyACI: Router's VRF resolves in the Tenant's BDs #")
	unmatched = {}
	bdcheck = self.apic.getBdOper(self.tenant_list)
	for tnt in self.tenant_list:
	    unmatched[tnt] = []
	    if [unmatched[tnt].append(bdname) for bdname in self.ntkNames\
                if '_%s_%s' %(self.apicsystemID,rtrIDs[tnt]) != bdcheck[tnt][bdname]['vrfname']\
                or bdcheck[tnt][bdname]['vrfstate'] != 'formed']:
		    LOG.error("\nStep-5-TC-2:Fail:VRF %s did NOT resolve in Tenant %s following BD %s >>"
                              %(rtrIDs[tnt],tnt,unmatched))
                    return unmatched

	LOG.info("\n# Step-6-TC-2: Add back the Routers's interfaces to the above new subnets #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(rtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetId) for subnetId in subnetIDs[tnt]]

	LOG.info("\nRemove the router interface from all but one subnet in each ntk #")

	LOG.info("\nVerifyACI: The BDs are STILL connected to Router's VRF #")

    def test_vpr_nat_func_3(self):
        """
        Testcase-3 in VPR-NAT Workflow
        """
        LOG.info("\n########  Testcase TEST_VPR_NAT_FUNC_3   ############\n"
		 "# Remove the router interfaces to keep it attached to only One Ntk  #\n"
		 "# VerifyACI: VRF for all but one BD's VRF resolves to *_shared   #\n"
		 "# Add new addtional Router in Tenant, attach to its unrouted BDs #n"
		 "# VerifyACI: Resp Router's VRF resolves in the Tenant's BDs      #\n"
		 "#####################################################\n")

    def test_vpr_nat_func_4(self):
        """
        Testcase-4 in VPR-NAT Workflow
        """
        LOG.info("\n########  Testcase TEST_VPR_NAT_FUNC_4   ############\n"
		 "# Remove the routers' interfaces from all attached networks  #\n"
		 "# VerifyACI: VRF for all BD's VRF resolves to *_shared   #\n"
		 "# Delete the routers					   #\n"
		 "# VerifyACI: VRFs of the deleted routers are deleted also  #\n"
		 "#####################################################\n")

if __name__ == "__main__":
    main()
