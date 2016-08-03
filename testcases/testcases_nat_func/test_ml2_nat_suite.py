#!/usr/bin/python

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
	self.ntkNames = {self.tnt1:['Net1','Net2','Net3'],
			 self.tnt2: ['ntk1','ntk2','ntk3']
			}
	self.subNames = {self.tnt1: ['Subnet1','Subnet2','Subnet3'],
			 self.tnt2: ['sub1','sub2','sub3']
			}
	self.apicsystemID = 'noirolab' #TODO: should auto fetch from neutron config
	self.defaultVrf = {self.tnt1:'shared',self.tnt2:'shared'}
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

        test_list = [self.test_vpr_nat_func_1,
		     self.test_vpr_nat_func_2,
		     self.test_vpr_nat_func_3,
		     self.test_vpr_nat_func_4]
        for test in test_list:
                if test() == 0:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'FAIL'
                    LOG.error("\n%s_%s == FAIL" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
		    sys.exit(1) #TBD: JISHNU should be removed later
                else:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'PASS'
                    LOG.info("\n%s_%s == PASS" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
        pprint.pprint(test_results)

    def verifyAciBDtoVRF(self,rtrid_dict):
	unmatched = {}
	bdcheck = self.apic.getBdOper(self.tenant_list)
	for tnt in self.tenant_list:
	    unmatched[tnt] = []
	    if [unmatched[tnt].append(bdname) for bdname in self.ntkNames[tnt]\
                if '_%s_%s' %(self.apicsystemID,rtrid_dict[tnt]) != bdcheck[tnt][bdname]['vrfname']\
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
	self.subnetIDs = {}
	self.networkIDs = {}
	for tnt in self.tenant_list:
	    #Every Network has just one Subnet, 1:1
	    self.subnetIDs[tnt] = []
	    self.networkIDs[tnt] = []
	    for index in range(len(self.ntkNames[tnt])):
	        netID = self.neutron.netcrud(self.ntkNames[tnt][index],'create',tnt)
		self.networkIDs[tnt].append(netID)
	        self.subnetIDs[tnt].append(self.neutron.subnetcrud(self.subNames[tnt][index],
		                        'create',
			                ntkNameId=netID,
					cidr=self.Cidrs[tnt][index],
					tenant=tnt))

	LOG.info("\n# Step-2:TC-1: Add Router for the tenants #")
	self.rtrIDs = {}
	for tnt in self.tenant_list:
	    _id = self.neutron.rtrcrud('RTR1','create',tenant=tnt)    
	    self.rtrIDs[tnt]= _id
	LOG.info("\nRouter IDs for the respective Tenants == %s" %(self.rtrIDs))

	LOG.info("\n# Step-3-TC-1:VerifyACI: VRF got created for this Router #")
	vrfnotfound = [self.rtrIDs[tnt] for tnt in self.tenant_list\
                if '_%s_%s' %(self.apicsystemID,self.rtrIDs[tnt])
		not in self.apic.getVrfs(tnt)[tnt]]
	if vrfnotfound:
	    LOG.info("\nStep-3-TC-1:Fail: Following VRFs not found in ACI = %s" %(vrfnotfound))
            return 0    

	LOG.info("\n# Step-4-TC-1:VerifyACI: BDs and their VRF resolves to *_shared #")
	unmatchedvrfs = self.verifyAciBDtoVRF(self.defaultVrf)
	if unmatchedvrfs:
	    LOG.error("\nStep-4-TC-1:Fail: Unresolved VRF for following BDs >> %s"
	              %(unmatchedvrfs))
	    return 0	     
	
	LOG.info("\n# Step-5-TC-1: Add resp Router Interfaces to Tenants' networks #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(self.rtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetId,tenant=tnt) for subnetId in self.subnetIDs[tnt]]

        LOG.info("\n# Step-6-TC-1: VerifyACI: Router's VRF resolves in the Tenant's BDs #")
	unmatchedvrfs = self.verifyAciBDtoVRF(self.rtrIDs)
	if unmatchedvrfs:
	    LOG.error("\nStep-6-TC-1:Fail: Unresolved VRF for following BDs >> %s"
	              %(unmatchedvrfs))
	    return 0	     

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
	    [self.neutron.rtrcrud(self.rtrIDs[tnt],'delete',rtrprop='interface',
			         subnet=subnetId,tenant=tnt) for subnetId in self.subnetIDs[tnt]]

	LOG.info("\n# Step-2-TC-2:VerifyACI: VRF for each BD VRF resolves to *_shared #")
	unmatchedvrfs = self.verifyAciBDtoVRF(self.defaultVrf)
	if unmatchedvrfs:
	    LOG.error("\nStep-2-TC-2:Fail: Unresolved VRF for following BDs >> %s"
	              %(unmatchedvrfs))
	    return 0	     
	
	LOG.info("\n# Step-3-TC-2: Add new subnet to the respective tenants's ntks #")
	# Duplicate subnets across tenants
	self.newCidrs = ['101.101.101.0/28','102.102.102.0/28','103.103.103.0/28']
	self.newSubNames = ['newSub1','newSub2','newSub3']
	self.new_subnetIDs = {}
	for tnt in self.tenant_list:
	    self.new_subnetIDs[tnt] = []
	    for index in range(len(self.newSubNames)):
	        self.new_subnetIDs[tnt].append(self.neutron.subnetcrud(
				        self.newSubNames[index],
                                        'create',
                                        ntkNameId=self.networkIDs[tnt][index],
                                        cidr=self.newCidrs[index],
                                        tenant=tnt))	

	LOG.info("\n# Step-4-TC-2: Add back the Routers's interfaces to the above new subnets #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(self.rtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetId,tenant=tnt) for subnetId in self.new_subnetIDs[tnt]]

        LOG.info("\n# Step-5-TC-2: VerifyACI: Router's VRF resolves in the Tenant's BDs #")
	unmatchedvrfs = self.verifyAciBDtoVRF(self.rtrIDs)
	if unmatchedvrfs:
	    LOG.error("\nStep-5-TC-2:Fail:VRFs did NOT resolve in following BD >> %s"
	              %(unmatchedvrfs))
	    return 0	     

	LOG.info("\n# Step-6-TC-2: Add back the Routers's interfaces to existing Old subnets of tenants #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(self.rtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetId,tenant=tnt) for subnetId in self.subnetIDs[tnt]]
	#TBD: Step 7(Verify in Neutron router-ports are connected to multiple subnets
	LOG.info("\nStep-8-TC-2: Remove the router interface from all but one subnet in each ntk #")
	for tnt in self.tenant_list:
            [self.neutron.rtrcrud(self.rtrIDs[tnt],'delete',rtrprop='interface',
                                 subnet=subnetId,tenant=tnt) for subnetId in self.new_subnetIDs[tnt]]

	LOG.info("\nStep-9-TC-2VerifyACI: The BDs are STILL connected to Router's VRF #")
	unmatchedvrfs = self.verifyAciBDtoVRF(self.rtrIDs)
	if unmatchedvrfs:
	    LOG.error("\nStep-9-TC-2:Fail:VRFs did NOT resolve in following BD >> %s"
	              %(unmatchedvrfs))
	    return 0	     

    def test_vpr_nat_func_3(self):
        """
        Testcase-3 in VPR-NAT Workflow
        """
        LOG.info("\n########  Testcase TEST_VPR_NAT_FUNC_3   ############\n"
		 "# Remove the router interfaces to keep it attached to only One Ntk  #\n"
		 "# VerifyACI: VRF for all but one BD's VRF resolves to *_shared   #\n"
		 "# Add new addtional Router in Tenant, attach to its unrouted BDs #n"
		 "# VerifyACI: VRF got created for the new router in ACI           #\n"
		 "# VerifyACI: Resp new Router's VRF resolves in the Tenant's BDs  #\n"
		 "#####################################################\n")

        LOG.info("\n Execution of Testcase starts #")
	LOG.info("\n# Step-1-TC-3: Remove the router interfaces to keep it attached to only One Ntk #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(self.rtrIDs[tnt],'delete',rtrprop='interface',
			         subnet=subnetName,tenant=tnt) for subnetName  in self.subNames[tnt][1:]]
	
	LOG.info("\nStep-2-TC-3: VerifyACI: VRF for all but one BD's VRF resolves to *_shared #")
	unmatched = {}
	bdcheck = self.apic.getBdOper(self.tenant_list)
	for tnt in self.tenant_list:
	    unmatched[tnt] = []
	    if [unmatched[tnt].append(bdname) for bdname in self.ntkNames[tnt][0]\
                if '_%s_%s' %(self.apicsystemID,self.rtrIDs[tnt]) != bdcheck[tnt][bdname]['vrfname']\
                or bdcheck[tnt][bdname]['vrfstate'] != 'formed']:
		LOG.info("\nStep-2-TC-3:Fail:Following BDs are not associated with correct VRF = %s" %(unmatched))
                return 0
	    if [unmatched[tnt].append(bdname) for bdname in self.ntkNames[tnt][1:]\
		if '_%s_%s' %(self.apicsystemID,'shared') != bdcheck[tnt][bdname]['vrfname']\
		or bdcheck[tnt][bdname]['vrfstate'] != 'formed']:
                LOG.info("\nStep-2-TC-3:Fail:Following BDs are not associated with 'shared' VRF = %s" %(unmatched))
                return 0

	LOG.info("\nStep-3-TC-3: Add new addtional Router in Tenant, attach to its unrouted BDs #")
	self.newrtrIDs = {}
	for tnt in self.tenant_list:
	    _id = self.neutron.rtrcrud('RTR2','create',tenant=tnt)    
	    self.newrtrIDs[tnt]= _id
	LOG.info("\n2nd Router IDs for the respective Tenants == %s" %(self.newrtrIDs))

	LOG.info("\n# Step-4-TC-3:VerifyACI: VRF got created for this Router #")
	vrfnotfound = [self.newrtrIDs[tnt] for tnt in self.tenant_list\
                if '_%s_%s' %(self.apicsystemID,self.newrtrIDs[tnt])
		not in self.apic.getVrfs(tnt)[tnt]]
	if vrfnotfound:
	    LOG.info("\nStep-4-TC-3:Fail: Following VRFs not found in ACI = %s" %(vrfnotfound))
            return 0    
	
	LOG.info("\n Step-5-TC-3: Attach new router to the networks which are in *_shared vrf")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(self.newrtrIDs[tnt],'add',rtrprop='interface',
			         subnet=subnetName,tenant=tnt) for subnetName in self.subNames[tnt][1:]]
	
	LOG.info("\nStep-6-TC-3: Resp new Router's VRF resolves in the Tenant's BDs #")
	unmatched = {}
	bdcheck = self.apic.getBdOper(self.tenant_list)
	for tnt in self.tenant_list:
	    unmatched[tnt] = []
	    if [unmatched[tnt].append(bdname) for bdname in self.ntkNames[tnt][1:]\
                if '_%s_%s' %(self.apicsystemID,self.rtrIDs[tnt]) != bdcheck[tnt][bdname]['vrfname']\
                or bdcheck[tnt][bdname]['vrfstate'] != 'formed']:
		LOG.info("\nStep-6-TC-3:Fail:Following BDs are not associated with correct VRF = %s" %(unmatched))
		return 0
	
    def test_vpr_nat_func_4(self):
        """
        Testcase-4 in VPR-NAT Workflow
        """
        LOG.info("\n########  Testcase TEST_VPR_NAT_FUNC_4   ###################\n"
		 "# Remove the routers' interfaces from all attached networks  #\n"
		 "# VerifyACI: VRF for all BD's VRF resolves to *_shared       #\n"
		 "# Delete all the routers                                     #\n"
		 "# VerifyACI: VRFs of the deleted routers are deleted also    #\n"
		 "##############################################################\n")

	LOG.info("\n Execution of Testcase starts #")
	LOG.info("\n Step-1-TC-4: Remove the routers' interfaces from all attached networks #")
	for tnt in self.tenant_list:
	    [self.neutron.rtrcrud(self.newrtrIDs[tnt],'delete',rtrprop='interface',
			         subnet=subnetName,tenant=tnt) for subnetName in self.subNames[tnt][1:]]
	    [self.neutron.rtrcrud(self.rtrIDs[tnt],'delete',rtrprop='interface',
				subnet=subnetName,tenant=tnt) for subnetName in self.subNames[tnt][0]]
	
	LOG.info("\n# Step-2-TC-4:VerifyACI: VRF for all BD's VRF resolves to *_shared #")
	unmatchedvrfs = self.verifyAciBDtoVRF(self.defaultVrf)
	if unmatchedvrfs:
	    LOG.error("\nStep-2-TC-4:Fail: Unresolved VRF for following BDs >> %s" %(unmatchedvrfs))
	    return 0	     

	#Merging the two dicts rtrIDs & newrtrIDs
	mergedDict = {}
	for k in self.rtrIDs.iterkeys(): #where k/key = tenant
	    mergedDict[k] = [self.rtrIDs[k],self.newrtrIDs[k]]

	LOG.info("\nStep-3-TC-4: Delete all the routers #")
	[self.neutron.rtrcrud(rtr,'create',tenant=tnt) for rtr in mergedDict[tnt]\
	 for tnt in self.tenant_list]

	LOG.info("\n# Step-4-TC-4:VerifyACI: VRF got created for this Router #")
	vrfnotfound = [rtr for rtr in mergedDict[tnt] for tnt in self.tenant_list\
                if '_%s_%s' %(self.apicsystemID,rtr)
		not in self.apic.getVrfs(tnt)[tnt]]
	if len(vrfnotfound) != 2:
	    LOG.info("\nStep-4-TC-4:Fail: Following Routers' VRF stale in ACI = %s" %(vrfnotfound))
            return 0    

if __name__ == "__main__":
    main()
