#!/usr/bin/python

import datetime
import logging
import optparse
import pprint
import string
import sys
import yaml
from time import sleep
from libs.gbp_utils import *
from libs.gbp_fab_traff_libs import gbpFabTraff
from natfuncglobalcfg import GbpNatFuncGlobalCfg
from natfunctestmethod import *
from testcases.config import conf

L3OUT1=conf.get('primary_L3out')
L3OUT1_NET=conf.get('primary_L3out_net')
L3OUT2=conf.get('secondary_L3out')
L3OUT2_NET=conf.get('secondary_L3out_net')

LOG.setLevel(logging.INFO)

def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--flag",
                      help="default_ext_seg_name "\
                      "Valid strings: <yes>",
                      dest='defextsegname')
    (options, args) = parser.parse_args()

    if options.defextsegname == 'yes':
       flag = 'default_external_segment_name'
       suite=NatGbpTestSuite()
    else:
       suite=NatGbpTestSuite()
    suite.test_runner()

class NatGbpTestSuite(object):
    
    def __init__(self,flag=''):
        self.extrtr = EXTRTR
        self.extrtr_ip1 = EXTRTR_IP1
        self.extrtr_ip2 = EXTRTR_IP2
	self.gwip1_extrtr = GWIP1_EXTRTR
	self.gwip2_extrtr = GWIP2_EXTRTR
        self.ntknode = NTKNODE
        self.apicip = APICIP
        self.avail_zone = AVAIL_ZONE
        self.pausetodbg = PAUSETODEBG
        self.natpoolname = NATPOOLNAME2
        self.fipsubnet1 = NATIPPOOL1
        self.fipsubnet2 = NATIPPOOL2
        self.targetiplist = [self.extrtr_ip1, self.extrtr_ip2]
        self.globalcfg = GbpNatFuncGlobalCfg()
        self.steps = NatFuncTestMethods()
        self.forextrtr = gbpFabTraff()
        self.flag=flag
	self.plugin = PLUGIN_TYPE
        
    def test_runner(self):
        """
        Method to run the Testcase in Ordered Steps
        """
        # Initiate Blind Cleanup of the testbed config
        # Ignoring this Initial Blind-Cleanup
        self.steps.DeleteOrCleanup('cleanup') 
        self.globalcfg.cleanup()
        # Initiate Global Configuration 
	if self.plugin:
	    if not self.steps.create_external_networks():
	  	sys.exit(1)
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
		     self.test_snat_func_10,
		     self.test_snat_func_11,
                     self.test_snat_func_12
                     ]
        if self.flag:
           self.steps.addhostpoolcidr(flag=self.flag)
        matchsnat = 0
        for test in test_list:
                # Below clean-up needed to remove any stale from prev tests
                self.steps.DeleteOrCleanup('cleanup')
                if 'snat' in test.__name__.lstrip('self.'):
                #intent of the below 'if' block: to call addhostpoolcidr
                #ONLY on match of first testcase which has 'snat' so that
                #so that on subsequent SNAT TCs you need not add host_pool
                    matchsnat += 1
                    if matchsnat == 1:
			if not self.plugin:
                            self.steps.addhostpoolcidr()
                if test() == 0: #Explicit check since test_func does not return 1/True
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'FAIL'
                    LOG.error("\n///// %s_%s == FAIL ////" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
                    if self.pausetodbg:
                        PauseToDebug()
                    self.steps.DeleteOrCleanup('cleanup')
                else:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'PASS'
                    LOG.info("\n**** %s_%s == PASS ****" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
        pprint.pprint(test_results)
        self.steps.DeleteOrCleanup('cleanup')
	if not self.plugin:
            self.steps.addhostpoolcidr(delete=True)
        # Fix external routes
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          SNATPOOL,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet2,
                                          self.gwip2_extrtr,
                                          action='update'
                                          )
        self.globalcfg.cleanup()

    def test_nat_func_1(self):
        """
        Testcase-1 in NAT Functionality
        """
        LOG.info(
        "\n **** Execution of Testcase TEST_NAT_FUNC_1 starts ****")
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        #NOTE:The below flag check cannot be applied in test-workflows
        #where ExtSeg is created after the L3Policies, else L3Ps will not
        #have ExtSeg association.
        if self.flag != 'default_external_segment_name':
            if not self.steps.testAssociateExtSegToBothL3ps():
               return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
                                   ):
               return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testLaunchVmsForEachPt():
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
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs(release_fip=False):
           return 0
        sleep(10)
        #Inter-change of FIPs
        if not self.steps.testAssociateFipToVMs(ic=True):
           return 0
        sleep(10)
        LOG.info(
        "\n DNATed Traffic from ExtRTR to VMs after Inter-Change of FIPs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
       
    def test_nat_func_2(self):
        """
        Testcase-2 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_2 starts ****")
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if self.flag != 'default_external_segment_name':
            if not self.steps.testAssociateExtSegToBothL3ps():
               return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
                                   ):
               return 0
        if not self.steps.testLaunchVmsForEachPt(az2=self.avail_zone):
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
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_3(self):
        """
        Testcase-3 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_3 starts ****")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt(az2=self.avail_zone):
           return 0
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
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
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0


    def test_nat_func_4(self):
        """
        Testcase-4 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_4 starts ****")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt(az2=self.avail_zone):
           return 0
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
                                   ):
               return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if self.steps.testAssociateFipToVMs(): #Negative Check
	    LOG.error(
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
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_5(self):
        """
        Testcase-5 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_5 starts ****")
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
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
                                   PRS_ICMP_TCP
                                   ):
               return 0
        if not self.steps.testLaunchVmsForEachPt(az2=self.avail_zone):
           return 0
        if self.flag != 'default_external_segment_name':
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
        DcExtsegid = self.steps.testCreateExtSegWithDefault(EXTSEG_SEC)
        if not DcExtsegid:
           return 0
        print 'DcExtSegID ==',DcExtsegid
        if not self.steps.testAssociateExtSegToBothL3ps(extsegid=DcExtsegid):
           return 0
        if not self.steps.testUpdateNatPoolAssociateExtSeg(DcExtsegid):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy(extseg=DcExtsegid,
                                                        extpol=''):
           return 0
        if not self.steps.testApplyUpdatePrsToPtg(
                                   'external',
                                   PRS_ICMP_TCP
                                   ):
           return 0
        if not self.steps.testAssociateFipToVMs(ExtSegName=EXTSEG_SEC):
           return 0
        sleep(10)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip2_extrtr,
                                          action='update'
                                          )
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_6(self):
        """
        Testcase in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_6 starts ****")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        #Intentionally launching VMs in same avail-zone/comp-node
        if not self.steps.testLaunchVmsForEachPt():
           return 0
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
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
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0
        self.steps.testDeleteNatPool()
        if not self.steps.testCreateNatPoolAssociateExtSeg(
                                   poolname=self.natpoolname,
                                   natpool=self.fipsubnet2
                                   ):
           return 0
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(30)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet2,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        #Verifying DNATed Traffic from both VMs
        LOG.info(
        "\n DNATed Traffic from ExtRTR to VMs with FIPs from New NAT-Pool")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0

        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_7(self):
        """
        Testcase-7 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_7 starts ****")
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if self.flag != 'default_external_segment_name':
            if not self.steps.testAssociateExtSegToBothL3ps():
               return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
                                   ):
               return 0
        if not self.steps.testCreateNsp():
           return 0
        if not self.steps.testApplyRemoveNSpFromPtg():
           return 0
        if not self.steps.testVerifyCfgdObjects():
           return 0
        if not self.steps.testLaunchVmsForEachPt(az2=self.avail_zone):
           return 0
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          self.fipsubnet1,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testApplyRemoveNSpFromPtg(nspuuid=None):
           return 0
        sleep(5)
        if not self.steps.testAssociateFipToVMs():
           return 0
        sleep(30)
        #Verifying DNATed Traffic from both VMs
        LOG.info(
        "\n DNATed Traffic from ExtRTR to VMs after NSP is removed from PTG")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testDisassociateFipFromVMs():
           return 0

    def test_nat_func_8(self):
        """
        Testcase-8 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_8 starts ****")
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testLaunchVmsForEachPt(az2=self.avail_zone):
           return 0
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
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
        #Verifying DNATed Traffic from both VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy(delete=1):
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        if not self.steps.testApplyUpdatePrsToPtg('external',
                                              PRS_ICMP_TCP
                                              ):
           return 0
        sleep(20) #Above update takes time to take effect on the ACI side
        #Verifying DNATed Traffic from both VMs
        LOG.info(
        "\n DNATed Traffic from ExtRTR to VMs after ExtPol is re-created")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0

    def test_snat_func_9(self):
        """
        Testcase-9 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_9 starts ****")
        
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
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
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
                                   ):
               return 0
        if self.flag != 'default_external_segment_name':
            if not self.steps.testAssociateExtSegToBothL3ps():
               return 0
        if not self.steps.testVerifyCfgdObjects(nat_type='snat'):
           return 0
        sleep(15)
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          SNATPOOL,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        #Verifying SNATed Traffic from both VMs
        LOG.info("\n SNATed Traffic from VMs to ExtRTR")
        if not self.steps.testTrafficFromVMsToExtRtr(self.targetiplist):
           return 0
        
    def test_snat_func_10(self):
        """
        Testcase-10 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_10 starts ****")
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
           return 0
        if not self.steps.testCreateNatPoolAssociateExtSeg():
           return 0
        if not self.steps.testCreatePtgDefaultL3p():
           return 0
        if not self.steps.testCreateNonDefaultL3pAndL2p():
           return 0
        if not self.steps.testCreatePtgWithNonDefaultL3p():
           return 0
        if self.flag != 'default_external_segment_name':
            if not self.steps.testAssociateExtSegToBothL3ps():
               return 0
        if not self.steps.testCreatePolicyTargetForEachPtg():
           return 0
        if not self.steps.testCreateUpdateExternalPolicy():
           return 0
        for ptgtype in ['internal','external']:
            if not self.steps.testApplyUpdatePrsToPtg(
                                   ptgtype,
                                   PRS_ICMP_TCP
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
                                          SNATPOOL,
                                          self.gwip1_extrtr,
                                          action='update'
                                          )
        #Verifying SNATed Traffic from both VMs
        LOG.info("\n SNATed Traffic from VMs to ExtRTR")
        if not self.steps.testTrafficFromVMsToExtRtr(self.targetiplist):
           return 0
        #Verifying DNATed Traffic from ExtRtr to VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
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
	#Verifying Traffic to be SNATed on DisAsso FIPs
        LOG.info(
        "\n SNATed Traffic from VMs to ExtRTR post FIPs disassociated")
        if not self.steps.testDisassociateFipFromVMs():
           return 0
        if not self.steps.testTrafficFromVMsToExtRtr(self.targetiplist):
           return 0

    def test_snat_func_11(self):
       """
       TBD:This Test will be done with Additing additional Subnets to ExtSeg
       TBD: Reach out to Sumit
       """

    def test_snat_func_12(self):
        """
        Testcase-12 in NAT Functionality
        """
        LOG.info(
        "\n**** Execution of Testcase TEST_NAT_FUNC_12 starts ****")
        #NOTE: For this TC, want to add host_pool_cidr to the L3out
        #while remove it from L3out1(this was already added by
        #test_runner func).Ensure to list this TC as the last TC to run
	if not self.plugin:
            self.steps.addhostpoolcidr(delete=True,flag=self.flag)
            self.steps.addhostpoolcidr(l3out=EXTSEG_SEC)
        if not self.steps.testCreateExtSegWithDefault(EXTSEG_PRI):
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
                                   PRS_ICMP_TCP
                                   ):
               return 0
        self.steps.AddSShContract(self.apicip) ## Adding SSH contract
        if not self.steps.testLaunchVmsForEachPt(az2=self.avail_zone):
           return 0
        if self.flag != 'default_external_segment_name':
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
        #Verify DNATed traffic from ExtRtr to all VMs
        LOG.info("\n DNATed Traffic from ExtRTR to VMs")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr):
           return 0
        DcExtsegid = self.steps.testCreateExtSegWithDefault(EXTSEG_SEC)
        if not DcExtsegid:
           return 0
        print 'DcExtSegID ==',DcExtsegid
        if not self.steps.testCreateUpdateExternalPolicy(extseg=DcExtsegid,
                                                         extpol='nondefault'):
           return 0
        if not self.steps.testApplyUpdatePrsToPtg(
                                   'external',
                                   PRS_ICMP_TCP
                                   ):
           return 0
        if not self.steps.testDisassociateFipFromVMs(vmname=True,
                                                     release_fip=False):
           return 0
        if not self.steps.testAssociateExtSegToBothL3ps(extsegid=DcExtsegid,
                                                        both=False):
           return 0
        #Verify DNATed traffic from ExtRtr to 1 VM on L3out1
        LOG.info(
        "\n DNATed Traffic from ExtRTR to the ONLY VM with FIP")
        if not self.steps.testTrafficFromExtRtrToVmFip(self.extrtr,fip=True):
           return 0
        #Verify SNATed traffic from ExtRtr to 1 VM on the L3out2
        LOG.info(
        "\n SNATed Traffic from the ONLY VM without FIP to ExtRtr")
        self.forextrtr.add_route_in_extrtr(
                                          self.extrtr,
                                          SNATPOOL,
                                          self.gwip2_extrtr,
                                          action='update'
                                          )
        if not self.steps.testTrafficFromVMsToExtRtr(self.targetiplist):
           return 0

if __name__ == "__main__":
    main()
