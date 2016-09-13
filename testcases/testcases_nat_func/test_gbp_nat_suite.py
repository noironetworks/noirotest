#!/usr/bin/python

import datetime
import logging
import pprint
import string
import sys
import yaml
from time import sleep
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_utils import *
from libs.gbp_fab_traff_libs import Gbp_def_traff
from natfuncglobalcfg import GbpNatFuncGlobalCfg
from natfunctestmethod import NatFuncTestMethods

def main():
    cfgfile = sys.argv[1]
    suite=NatGbpTestSuite(cfgfile)
    suite.test_runner()

class NatGbpTestSuite(object):
    
    def __init__(self,cfgfile):
        with open(cfgfile, 'rt') as f:
            conf = yaml.load(f)
        self.cntlrip = conf['controller_ip']
        self.extrtr = conf['ext_rtr']
        self.extrtr_ip1 = conf['extrtr_ip1']
        self.extrtr_ip2 = conf['extrtr_ip2']
	self.gwip1_extrtr = conf['gwip1_extrtr']
	self.gwip2_extrtr = conf['gwip2_extrtr']
        self.targetiplist = [self.extrtr_ip1, self.extrtr_ip2]
        self.ntknode = conf['network_node']
        self.apicip = conf['apic_ip']
        self.globalcfg = GbpNatFuncGlobalCfg(self.cntlrip)
        self.steps = NatFuncTestMethods(self.cntlrip,self.ntknode)
        self.natpoolname = self.steps.natpoolname2
        self.fipsubnet1 = self.steps.natippool1
        self.fipsubnet2 = self.steps.natippool2
        self.forextrtr = Gbp_def_traff()
        
    def test_runner(self):
        """
        Method to run the Testcase in Ordered Steps
        """
        # Initiate Blind Cleanup of the testbed config
        self.steps.DeleteOrCleanup('cleanup')
        self.globalcfg.cleanup()
        sys.exit(1)
        # Initiate Global Configuration 
        self.globalcfg.CfgGlobalObjs() 
        test_results = {}
        test_list = [self.test_nat_func_1,
                     self.test_nat_func_2,
                     self.test_nat_func_3,
		     self.test_nat_func_4,
		     self.test_nat_func_5,
		     self.test_nat_func_6,
		     self.test_nat_func_7,
		     self.test_nat_func_8,
		     self.test_snat_func_9,
		     self.test_snat_func_10
                     ]
        for test in test_list:
                self.steps.DeleteOrCleanup('cleanup')
                matchsnat = 0
                if 'snat' in test.__name__.lstrip('self.'): #intent of the below if block: to call addhostpoolcidr on first match
                    matchsnat += 1
                    if matchsnat == 1:
                       self.steps.addhostpoolcidr()
                if test():
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'FAIL'
                    self.steps._log.error("\n///// %s_%s == FAIL ////" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
                    self.steps.DeleteOrCleanup('cleanup')
                else:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'PASS'
                    self.steps._log.info("\n**** %s_%s == PASS ****" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
        pprint.pprint(test_results)
        self.globalcfg.cleanup()

    def test_nat_func_1(self):
        """
        Testcase-1 in NAT Functionality
        """
        self.steps._log.info(
        "\n **** Execution of Testcase TEST_NAT_FUNC_1 starts ****")
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(10)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0
       
    def test_nat_func_2(self):
        """
        Testcase-2 in NAT Functionality
        """
        self.steps._log.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_2 starts ****")
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(10)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_3(self):
        """
        Testcase-3 in NAT Functionality
        """
        self.steps._log.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_3 starts ****")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(10)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0


    def test_nat_func_4(self):
        """
        Testcase-4 in NAT Functionality
        """
        self.steps._log.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_4 starts ****")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if self.steps.testAssociateFipToVMs(): #Negative Check
	   self.steps._log.error(
           "\n Expected FIP Association To Fail,"
           " since L3P is NOT yet associated to ExtSeg")
           return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(10)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_5(self):
        """
        Testcase-5 in NAT Functionality
        """
        self.steps._log.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_5 starts ****")
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(10)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs(release_fip=1):
           return 0
        DcExtsegid = self.steps.testCreateExtSegWithDefault('Datacenter-Out')
        if not DcExtsegid:
           return 0
        print 'DcExtSegID ==',DcExtsegid
        if not self.steps.testAssociateExtSegToBothL3ps(extsegid=DcExtsegid):
           return 0
        if not self.steps.testUpdateNatPoolAssociateExtSeg(DcExtsegid):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy(update=1,updextseg=DcExtsegid):
           return 0
        if not self.steps.testAssociateFipToVMs(ExtSegName='Datacenter-Out'):
           return 0
        sleep(10)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip2_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_6(self):
        """
        Testcase in NAT Functionality
        """
        self.steps._log.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_6 starts ****")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(30)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs(release_fip=1):
           return 0
        self.steps.testDeleteNatPool()
        if not self.steps.testCreateNatPoolAssociateExtSeg(
                                   poolname=self.natpoolname,
                                   natpool=self.fipsubnet2
                                   ):
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(40)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet2,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0

        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_7(self):
        """
        Testcase-7 in NAT Functionality
        """
        self.steps._log.info(
              "\nExecution of Testcase TEST_NAT_FUNC_7 starts")
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testCreateNsp():
           return 0
        if not self.steps.testApplyRemoveNSpFromPtg():
           return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(40)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr,vmfips=1):
           return 0
        if not self.steps.testApplyRemoveNSpFromPtg(nspuuid=None):
           return 0
        sleep(5)
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(40)
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs(release_fip=1):
           return 0

    def test_nat_func_8(self):
        """
        Testcase-8 in NAT Functionality
        """
        self.steps._log.info(
              "\nExecution of Testcase TEST_NAT_FUNC_8 starts")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(30)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy(delete=1):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        if not self.steps.testApplyUpdatePrsToPtg('external',
                                              self.globalcfg.prsicmptcp
                                              ):
           return 0
        sleep(20) #Above update takes time to take effect on the ACI side
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0

    def test_snat_func_9(self):
        """
        Testcase-9 in NAT Functionality
        """
        self.steps._log.info(
                  "\nExecution of Testcase TEST_NAT_FUNC_9 starts")
        
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        
        self.steps.AddSShContract(self.apicip) ## Adding SSH contract
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        print "Sleeping for VM to come up ..."
        sleep(10)
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testVerifyCfgdObjects(nat_type='snat'):
           return 0
        sleep(15)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.steps.snatpool,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromVMsToExtRtr(self.targetiplist):
           return 0
        
    def test_snat_func_10(self):
        """
        Testcase-10 in NAT Functionality
        """
        self.steps._log.info(
                  "\nExecution of Testcase TEST_NAT_FUNC_10 starts")
        if not self.steps.testCreateExtSegWithDefault('Management-Out'):
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testAssociateExtSegToBothL3ps():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   self.globalcfg.prsicmptcp
                                   ):
               return 0
        if not self.steps.testVerifyCfgdObjects(nat_type='snat'):
           return 0
        self.steps.AddSShContract(self.apicip) ## Adding SSH contract
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        sleep(15)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.steps.snatpool,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        #Verifying SNATed Traffic from both VMs
        if not self.steps.testTrafficFromVMsToExtRtr(self.targetiplist):
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(30)
        #Verifying DNATed Traffic from ExtRtr to VMs
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet2,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
	#Verifying Traffic to be SNATed on DisAsso FIPs
        if not self.steps.testDisassociateFipFromVMs():
           return 0
        if not self.steps.testTrafficFromVMsToExtRtr(self.targetiplist):
           return 0

if __name__ == "__main__":
    main()
