#!/usr/bin/env python

import sys
import logging
import os
import datetime
import pprint
import string
from libs.gbp_crud_libs import GBPCrud
from traff_from_allvms import NatTraffic
import uuid
from libs.gbp_utils import *
from testcases.config import conf

L3OUT1=conf.get('primary_L3out')
L3OUT1_NET=conf.get('primary_L3out_net')
L3OUT2=conf.get('secondary_L3out')
L3OUT2_NET=conf.get('secondary_L3out_net')


class SNAT_VMs_to_ExtGw(object):

    # Initialize logging
    # logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.setLevel(logging.INFO)
    # create a logfile handler
    hdlr = logging.FileHandler('/tmp/testsuite_snat_vms_to_extgw.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    hdlr.setFormatter(formatter)
    # Add the handler to the logger
    _log.addHandler(hdlr)

    def __init__(self, objs_uuid):
        """
        Traffic Test Class between ExternalGWRtr and Tenant VM
        VMs/Endpoints behind Border and Non-Border Leaf
        In this class we send Traffic b/w ExtGWRtr and end-points Web-Server(compnode-1)
        And App-Server(compnode-2)
        """
        self.extgwrtr = objs_uuid['external_gw']
        self.ostack_controller = objs_uuid['ostack_controller']
        self.network_node = objs_uuid['network_node']
        self.ext_seg_1 = objs_uuid['mgmt_external_segment_id']
        self.ext_seg_2 = objs_uuid['dc_external_segment_id']
        self.external_pol_1 = objs_uuid['mgmt_external_policy_id']
        self.external_pol_2 = objs_uuid['dc_external_policy_id']
        self.websrvr_ptg = objs_uuid['web_srvr_ptg_id']
        self.webclnt_ptg = objs_uuid['web_clnt_ptg_id']
        self.appsrvr_ptg = objs_uuid['app_ptg_id']
        self.test_2_prs = {objs_uuid['shared_ruleset_norule_id']}
        self.test_3_prs = {objs_uuid['shared_ruleset_icmp_id']}
        self.test_4_prs = {objs_uuid['shared_ruleset_tcp_id']}
        self.test_5_prs = {objs_uuid['shared_ruleset_icmp_tcp_id']}
        self.vm_list = ['App-Server', 'Web-Server',
                        'Web-Client-1', 'Web-Client-2']
        self.gbp_crud = GBPCrud(self.ostack_controller)
        self.extgwips = objs_uuid['ipsofextgw']
        self.pausetodebug = objs_uuid['pausetodebug']
        self.routefordest = objs_uuid['routefordest']
        self.nat_traffic = NatTraffic(
            self.ostack_controller, self.vm_list, self.network_node)

    def test_runner(self,preexist):
        """
        Method to run 
        """
        # Add external routes to the Shadow L3Out(only for L3OUT2)
        self.gbp_crud.AddRouteInShadowL3Out(self.ext_seg_2,
                                                      L3OUT2,
                                                      'snat',
                                                      self.routefordest
                                                       )

        # Note: Cleanup per testcases is not required,since every testcase
        # updates the PTG, hence over-writing previous attr vals
        test_list = [
            self.test_1_traff_with_no_prs,
            self.test_2_traff_app_prs_no_rule,
            self.test_3_traff_apply_prs_icmp,
            self.test_4_traff_apply_prs_tcp,
            self.test_5_traff_apply_prs_icmp_tcp,
            self.test_6_traff_apply_prs_icmp_tcp_with_jumbo,
            self.test_7_traff_rem_prs
        ]
        test_results = {}
        abort = 0
        for test in test_list:
                repeat_test = 1
                while repeat_test < 4:
                  if test() == 1:
                     break
                  if test() == 2:
                     abort = 1
                     break
                  self._log.warning("Repeat-on-fail Run of the Testcase = %s" %(test.__name__.lstrip('self.')))
                  if self.pausetodebug == True:
                     PauseToDebug()
                  repeat_test += 1
                if repeat_test == 4:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'FAIL'
                    self._log.error("\n%s_%s == FAIL" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
                elif abort == 1:
                     test_results[string.upper(test.__name__.lstrip('self.'))] = 'ABORT'
                     self._log.error("\n%s_%s == ABORT" % (
                         self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
                     break
                else:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'PASS'
                    self._log.info("\n%s_%s == PASS" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
        pprint.pprint(test_results)

    def test_1_traff_with_no_prs(self):
        """
        Run traff test with NO CONTRACT between External PTG & Tenant PTG
        """
        failed = []
        for srcvm in self.vm_list:
            self._log.info(
                "\nTestcase_SNAT_%s_TO_EXTGW: NO CONTRACT APPLIED and VERIFY TRAFFIC" % (srcvm))
            run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                srcvm, self.extgwips)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(srcvm))
               return 2
            if not isinstance(run_traffic, tuple):  # Negative check
                failed.append(srcvm)
        if len(failed) > 1:
            self._log.info(
                "\nFollowing Traffic Test with NO Contract Failed = %s" % (failed))
            return 0
        else:
            return 1

    def test_2_traff_app_prs_no_rule(self):
        """
        Update the in-use PTG with a PRS which has NO-Rule
        Send traff
        """
        self._log.info(
            "\nTestcase_Testcase_SNAT_VM_TO_EXTGW: APPLY CONTRACT BUT NO RULE and VERIFY TRAFFIC")
        prs = self.test_2_prs
        failed = []
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbp_crud.update_gbp_external_policy(ext_pol, property_type='uuid', consumed_policy_rulesets=prs) == 0:
                return 0
        for ptg in [self.websrvr_ptg, self.webclnt_ptg, self.appsrvr_ptg]:
            if self.gbp_crud.update_gbp_policy_target_group(ptg, property_type='uuid', provided_policy_rulesets=prs) == 0:
                return 0
        for srcvm in self.vm_list:
            self._log.info(
                "\nTestcase_SNAT_%s_TO_EXTGW: APPLY CONTRACT BUT NO RULE and VERIFY TRAFFIC" % (srcvm))
            run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                srcvm, self.extgwips)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(srcvm))
               return 2
            if not isinstance(run_traffic, tuple):  # Negative check
                failed.append(srcvm)
        if len(failed) > 1:
            self._log.info(
                "\nFollowing Traffic Test with NO Contract, Failed = %s" % (failed))
            return 0
        else:
            return 1

    def test_3_traff_apply_prs_icmp(self):
        """
        Apply Policy-RuleSet to the in-use PTG
        Send traffic
        """
        self._log.info(
            "\nTestcase_SNAT_VM_TO_EXTGW: APPLY ICMP CONTRACT and VERIFY TRAFFIC")
        prs = self.test_3_prs
        failed = {}
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbp_crud.update_gbp_external_policy(ext_pol, property_type='uuid', consumed_policy_rulesets=prs) == 0:
                return 0
        for ptg in [self.websrvr_ptg, self.webclnt_ptg, self.appsrvr_ptg]:
            if self.gbp_crud.update_gbp_policy_target_group(ptg, property_type='uuid', provided_policy_rulesets=prs) == 0:
                return 0
        for srcvm in self.vm_list:
            self._log.info(
                "\nTestcase_SNAT_%s_TO_EXTGW: APPLY ICMP CONTRACT and VERIFY TRAFFIC" % (srcvm))
            run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                srcvm, self.extgwips, proto='icmp')
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(srcvm))
               return 2
            if isinstance(run_traffic, tuple):
                failed[srcvm] = run_traffic[1]
        if len(failed) > 0:
            self._log.info(
                "\nFollowing Traffic Test Failed After Applying ICMP Contract == %s" % (failed))
            return 0
        else:
            return 1

    def test_4_traff_apply_prs_tcp(self):
        """
        Apply Policy-RuleSet to the in-use PTG
        Send traffic
        """
        self._log.info(
            "\nTestcase_SNAT_VM_TO_EXTGW: APPLY TCP CONTRACT and VERIFY TRAFFIC")
        prs = self.test_4_prs
        failed = {}
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbp_crud.update_gbp_external_policy(ext_pol, property_type='uuid', consumed_policy_rulesets=prs) == 0:
                return 0
        for ptg in [self.websrvr_ptg, self.webclnt_ptg, self.appsrvr_ptg]:
            if self.gbp_crud.update_gbp_policy_target_group(ptg, property_type='uuid', provided_policy_rulesets=prs) == 0:
                return 0
        for srcvm in self.vm_list:
            self._log.info(
                "\nTestcase_SNAT_%s_TO_EXTGW: APPLY TCP CONTRACT and VERIFY TRAFFIC" % (srcvm))
            run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                srcvm, self.extgwips, proto='tcp')
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(srcvm))
               return 2
            if isinstance(run_traffic, tuple):
                failed[srcvm] = run_traffic[1]
        if len(failed) > 0:
            self._log.info(
                "\nFollowing Traffic Test Failed After Applying TCP Contract == %s" % (failed))
            return 0
        else:
            return 1

    def test_5_traff_apply_prs_icmp_tcp(self):
        """
        Apply Policy-RuleSet to the in-use PTG
        Send traffic
        """
        self._log.info(
            "\nTestcase_SNAT_VM_TO_EXTGW: APPLY ICMP-TCP-Combo CONTRACT and VERIFY TRAFFIC")
        prs = self.test_5_prs
        failed = {}
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbp_crud.update_gbp_external_policy(ext_pol, property_type='uuid', consumed_policy_rulesets=prs) == 0:
                return 0
        for ptg in [self.websrvr_ptg, self.webclnt_ptg, self.appsrvr_ptg]:
            if self.gbp_crud.update_gbp_policy_target_group(ptg, property_type='uuid', provided_policy_rulesets=prs) == 0:
                return 0
        for srcvm in self.vm_list:
            self._log.info(
                "\nTestcase_SNAT_%s_TO_EXTGW: APPLY ICMP-TCP-Combo CONTRACT and VERIFY TRAFFIC" % (srcvm))
            run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                srcvm, self.extgwips)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(srcvm))
               return 2
            if isinstance(run_traffic, tuple):
                failed[srcvm] = run_traffic[1]
        if len(failed) > 0:
            self._log.info(
                "\nFollowing Traffic Test Failed After Applying ICMP-TCP-Combo Contract == %s" % (failed))
            return 0
        else:
            return 1

    def test_6_traff_apply_prs_icmp_tcp_with_jumbo(self):
        """
        Apply Policy-RuleSet to the in-use PTG
        Send traffic
        """
        self._log.info(
            "\nTestcase_SNAT_VM_TO_EXTGW_JUMBO: APPLY ICMP-TCP-Combo CONTRACT and VERIFY TRAFFIC with JUMBO")
        prs = self.test_5_prs
        failed = {}
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbp_crud.update_gbp_external_policy(ext_pol, property_type='uuid', consumed_policy_rulesets=prs) == 0:
                return 0
        for ptg in [self.websrvr_ptg, self.webclnt_ptg, self.appsrvr_ptg]:
            if self.gbp_crud.update_gbp_policy_target_group(ptg, property_type='uuid', provided_policy_rulesets=prs) == 0:
                return 0
        for srcvm in self.vm_list:
            self._log.info(
                "\nTestcase_SNAT_%s_TO_EXTGW_JUMBO: APPLY ICMP-TCP-Combo CONTRACT and VERIFY TRAFFIC with JUMBO" % (srcvm))
            run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                srcvm, self.extgwips,jumbo=1)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(srcvm))
               return 2
            if isinstance(run_traffic, tuple):
                failed[srcvm] = run_traffic[1]
        if len(failed) > 0:
            self._log.info(
                "\nFollowing Traffic Test Failed After Applying ICMP-TCP-Combo Contract for Jumbo Frames == %s" % (failed))
            return 0
        else:
            return 1

    def test_7_traff_rem_prs(self):
        """
        Remove the PRS/Contract from the PTG
        Test all traffic types
        """
        failed = {}
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbp_crud.update_gbp_external_policy(ext_pol, property_type='uuid',
                                                        consumed_policy_rulesets = None,
                                                        provided_policy_rulesets = None) == 0:
                return 0
        for ptg in [self.websrvr_ptg, self.webclnt_ptg, self.appsrvr_ptg]:
            if self.gbp_crud.update_gbp_policy_target_group(ptg, property_type='uuid',
                                                            provided_policy_rulesets = None,
                                                            consumed_policy_rulesets = None) == 0:
                return 0
        for srcvm in self.vm_list:
            self._log.info(
                "\nTestcase_SNAT_%s_TO_EXTGW: CONTRACT REMOVED and VERIFY TRAFFIC" % (srcvm))
            run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                srcvm, self.extgwips)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(srcvm))
               return 2
            if not isinstance(run_traffic, tuple):  # Negative check
                failed[srcvm] = run_traffic[1]
        if len(failed) > 1:
            self._log.info(
                "\nFollowing Traffic Test with Contract Removed, Failed = %s" % (failed))
            return 0
        else:
            return 1
