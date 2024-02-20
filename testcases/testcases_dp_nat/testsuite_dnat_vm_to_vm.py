#!/usr/bin/env python

import sys
import logging
import os
import datetime
import pprint
import string
from libs.gbp_nova_libs import gbpNova
from libs.gbp_crud_libs import GBPCrud
from traff_from_allvms import NatTraffic
from libs.gbp_utils import *
import uuid
from testcases.config import conf

L3OUT1=conf.get('primary_L3out')
L3OUT1_NET=conf.get('primary_L3out_net')
L3OUT2=conf.get('secondary_L3out')
L3OUT2_NET=conf.get('secondary_L3out_net')


class DNAT_VMs_to_VMs(object):

    # Initialize logging
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
    _log = logging.getLogger(__name__)
    hdlr = logging.FileHandler('/tmp/testsuite_dnat_vm_to_vms.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    _log.addHandler(hdlr)
    _log.setLevel(logging.INFO)

    def __init__(self, objs_uuid, dest_vm_fips):
        """
        Traffic Test Class between ExternalGWRtr and Tenant VM
        VMs/Endpoints behind Border and Non-Border Leaf
        In this class we send Traffic b/w ExtGWRtr and end-points Web-Server(compnode-1)
        And App-Server(compnode-2)
        """
        self.extgwrtr = objs_uuid['external_gw']
        self.ostack_controller = objs_uuid['ostack_controller']
        self.network_node = objs_uuid['network_node']
        self.external_pol_1 = objs_uuid['mgmt_external_policy_id']
        self.external_pol_2 = objs_uuid['dc_external_policy_id']
        self.ext_seg_1 = objs_uuid['mgmt_external_segment_id']
        self.ext_seg_2 = objs_uuid['dc_external_segment_id']
        self.websrvr_ptg = objs_uuid['web_srvr_ptg_id']
        self.webclnt_ptg = objs_uuid['web_clnt_ptg_id']
        self.appsrvr_ptg = objs_uuid['app_ptg_id']
        self.test_3_prs = {objs_uuid['shared_ruleset_icmp_id']}
        self.test_4_prs = {objs_uuid['shared_ruleset_tcp_id']}
        self.test_5_prs = {objs_uuid['shared_ruleset_icmp_tcp_id']}
        self.pausetodebug = objs_uuid['pausetodebug']
        self.routefordest = objs_uuid['routefordest']
        self.vmfortraff = ['App-Server', 'Web-Server', 'Web-Client-1', 'Web-Client-2']
        self.vmtuple = ('App-Server', 'Web-Server', 'Web-Client-1', 'Web-Client-2')
        # Note: vmfortraff & vmtuple could have been addressed as a single
        # datastructure. However inside Traff Lib we need a mutable ds. Thereby
        # when Traff Lib restores the inherited list from the parent class, the
        # original list was going out of order. That affected the testcase for loop.
        # So for the test case for loop resorted to a immutable ds, hence vmtuple
        # I could have still fixed this by taking care of insertion of the element
        # back to its original positional while restoring the inherited list, but
        # kept it simple but keeping two diff type of ds
        self.vm_to_ptg_dict = {
            'App-Server': self.appsrvr_ptg, 'Web-Server': self.websrvr_ptg,
            'Web-Client-1': self.webclnt_ptg, 'Web-Client-2': self.webclnt_ptg
        }
        self.dest_vm_fips = dest_vm_fips
        self.gbpcrud = GBPCrud(self.ostack_controller)
        self.gbpnova = gbpNova(self.ostack_controller)
        self.nat_traffic = NatTraffic(
            self.ostack_controller, self.vmfortraff, self.network_node)

    def test_runner(self, preexist):
        """
        Method to run all testcases
        """
        # Add external routes to the Shadow L3Out(only for L3OUT2)
        self.gbpcrud.AddRouteInShadowL3Out(self.ext_seg_2,
                                                      L3OUT2,
                                                      'dnat',
                                                      self.routefordest,
                                                      route='66.66.66.0/24',
                                                      ) #Hard-coded reference from yaml file param dc_nat_ip_pool

        # Note: Cleanup per testcases is not required,since every testcase
        # updates the PTG, hence over-writing previous attr vals
        test_list = [
            self.test_1_traff_with_no_prs,
            self.test_2_traff_apply_prs_icmp_extptgs_not_regptgs,
            self.test_3_traff_apply_prs_icmp,
            self.test_4_traff_apply_prs_tcp,
            self.test_5_traff_apply_prs_icmp_tcp,
            self.test_6_traff_rem_prs
        ]

        test_results = {}
        abort = 0
        for test in test_list:
                repeat_test = 1
                while repeat_test < 3:
                  if test() == 1:
                     break
                  if test() == 2:
                     abort = 1
                     break
                  self._log.warning("Repeat-on-fail Run of the Testcase = %s" %(test.__name__.lstrip('self.')))
                  if self.pausetodebug == True:
                     PauseToDebug()
                  repeat_test += 1
                if repeat_test == 3:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'FAIL'
                    self._log.error("\n%s_%s == FAIL" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
                elif abort == 1:
                     test_results[string.upper(test.__name__.lstrip('self.'))] = 'ABORT'
                     self._log.error("\n%s_%s == ABORT" % (
                         self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
                else:
                    test_results[string.upper(test.__name__.lstrip('self.'))] = 'PASS'
                    self._log.info("\n%s_%s == PASS" % (
                        self.__class__.__name__.upper(), string.upper(test.__name__.lstrip('self.'))))
        pprint.pprint(test_results)
        self.cleanup()

    def test_1_traff_with_no_prs(self):
        """
        Run traff test with NO CONTRACT between regular and external PTGs
        """
        failed = []
        for vm in self.vmtuple:
            self._log.info(
                "\nTestcase_DNAT_%s_to_RESTOFVMs: NO CONTRACT APPLIED and VERIFY TRAFFIC" % (vm))
            
            run_traffic = self.nat_traffic.test_traff_from_vm_to_allvms(
                vm, proto='icmp')
            """
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(vm))
               return 2
            if not isinstance(run_traffic, tuple):  # Negative check
                failed.append(vm)
            """
        if len(failed) > 1:
            self._log.info(
                "\nFollowing Traffic Test with NO Contract Failed for these Dest VMs = %s" % (failed))
            return 0
        else:
            return 1

    def test_2_traff_apply_prs_icmp_extptgs_not_regptgs(self):
        """
        ICMP Policy-RuleSet Provided and Consumed by the External PTGs
        The above Rule-Set is NOT Provided/Consumed by Regular PTGs
        Send traffic
        """
        failed = []
        prs = self.test_3_prs
        self._log.info(
            "\nExternal Policy needs to be consumed & provided the same prs = %s" % (prs))
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbpcrud.update_gbp_external_policy(ext_pol,
                                                        property_type='uuid',
                                                        provided_policy_rulesets=prs,
                                                        consumed_policy_rulesets=prs) == 0:
                return 0
        for vm in self.vmtuple:
            self._log.info(
                "\nTestcase_DNAT_%s_to_RESTOFVMs: ICMP CONTRACT NOT APPLIED on REG PTGs but Ext PTGs and VERIFY TRAFFIC" % (vm))
            run_traffic = self.nat_traffic.test_traff_from_vm_to_allvms(vm)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(vm))
               return 2
            if not isinstance(run_traffic, tuple):  # Negative check
                failed.append(vm)
        if len(failed) > 1:
            self._log.info(
                "\nFollowing Traffic Test with Contract cons/prov by ExtPTGs and not by RegPTG, Failed for these Dest VMs = %s" % (failed))
            return 0
        else:
            return 1

    def test_3_traff_apply_prs_icmp(self):
        """
        Apply ICMP Policy-RuleSet to the in-use PTG
        ICMP Policy-RuleSet Provided by PTG of VUT(VM under test)
        Consumed by PTG of Other VMs
        ICMP Policy-RuleSet Provided and Consumed by the External PTGs
        Send traffic
        """
        failed = {}
        prs = self.test_3_prs
        self._log.info(
            "\nExternal Policy needs to be consumed & provided the same prs = %s" % (prs))
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbpcrud.update_gbp_external_policy(ext_pol,
                                                        property_type='uuid',
                                                        provided_policy_rulesets=prs,
                                                        consumed_policy_rulesets=prs) == 0:
                return 0
        for vm in self.vmtuple:
            self._log.info(
                "\nTestcase_DNAT_%s_to_RESTOFVMs: APPLY ICMP CONTRACT and VERIFY TRAFFIC" % (vm))
            for vm_name, ptg in self.vm_to_ptg_dict.items():
                if vm_name != vm:
                    if self.gbpcrud.update_gbp_policy_target_group(ptg,
                                                                    property_type='uuid',
                                                                    consumed_policy_rulesets=prs,
                                                                    provided_policy_rulesets=None) == 0:
                        return 0
            if self.gbpcrud.update_gbp_policy_target_group(self.vm_to_ptg_dict[vm],
                                                            property_type='uuid',
                                                            provided_policy_rulesets=prs,
                                                            consumed_policy_rulesets=None) == 0:
                return 0
            run_traffic = self.nat_traffic.test_traff_from_vm_to_allvms(
                vm, proto='icmp')
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(vm))
               return 2
            if isinstance(run_traffic, tuple):
                failed[vm] = run_traffic[1]
        if len(failed) > 0:
            self._log.info(
                "\nFollowing Traffic Test Failed After Applying ICMP Contract == %s" % (failed))
            return 0
        else:
            return 1

    def test_4_traff_apply_prs_tcp(self):
        """
        Apply TCP Policy-RuleSet to the in-use PTG
        TCP Policy-RuleSet Provided by PTG of VUT(VM under test)
        Consumed by PTG of Other VMs
        Send traffic
        """
        failed = {}
        prs = self.test_4_prs
        self._log.info(
            "\nExternal Policy needs to be consumed & provided the same prs = %s" % (prs))
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbpcrud.update_gbp_external_policy(ext_pol,
                                                        property_type='uuid',
                                                        provided_policy_rulesets=prs,
                                                        consumed_policy_rulesets=prs) == 0:
                return 0
        for vm in self.vmtuple:
            self._log.info(
                "\nTestcase_DNAT_%s_to_RESTOFVMs: APPLY TCP CONTRACT and VERIFY TRAFFIC" % (vm))
            for vm_name, ptg in self.vm_to_ptg_dict.items():
                if vm_name != vm:
                    if self.gbpcrud.update_gbp_policy_target_group(ptg,
                                                                    property_type='uuid',
                                                                    consumed_policy_rulesets=prs,
                                                                    provided_policy_rulesets= None) == 0:
                        return 0
            if self.gbpcrud.update_gbp_policy_target_group(self.vm_to_ptg_dict[vm],
                                                            property_type='uuid',
                                                            provided_policy_rulesets=prs,
                                                            consumed_policy_rulesets=None) == 0:
                return 0
            run_traffic = self.nat_traffic.test_traff_from_vm_to_allvms(
                vm, proto='tcp')
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(vm))
               return 2
            if isinstance(run_traffic, tuple):
                failed[vm] = run_traffic[1]
        if len(failed) > 0:
            self._log.info(
                "\nFollowing Traffic Test Failed After Applying TCP Contract == %s" % (failed))
            return 0
        else:
            return 1

    def test_5_traff_apply_prs_icmp_tcp(self):
        """
        Apply TCP-ICMP-combo Policy-RuleSet to the in-use PTG
        TCP-ICMP-combo Policy-RuleSet Provided by PTG of VUT(VM under test)
        Consumed by PTG of Other VMs
        Send traffic
        """
        failed = {}
        prs = self.test_5_prs
        self._log.info(
            "\nExternal Policy needs to be consumed & provided the same prs = %s" % (prs))
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbpcrud.update_gbp_external_policy(ext_pol,
                                                        property_type='uuid',
                                                        provided_policy_rulesets=prs,
                                                        consumed_policy_rulesets=prs) == 0:
                return 0
        for vm in self.vmtuple:
            self._log.info(
                "\nTestcase_DNAT_%s_to_RESTOFVMs: APPLY TCP-ICMP-COMBO CONTRACT and VERIFY TRAFFIC" % (vm))
            for vm_name, ptg in self.vm_to_ptg_dict.items():
                if vm_name != vm:
                    if self.gbpcrud.update_gbp_policy_target_group(ptg,
                                                                    property_type='uuid',
                                                                    consumed_policy_rulesets=prs,
                                                                    provided_policy_rulesets= None) == 0:
                        return 0
            if self.gbpcrud.update_gbp_policy_target_group(self.vm_to_ptg_dict[vm],
                                                            property_type='uuid',
                                                            provided_policy_rulesets=prs,
                                                            consumed_policy_rulesets=None) == 0:
                return 0
            run_traffic = self.nat_traffic.test_traff_from_vm_to_allvms(vm)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(vm))
               return 2
            if isinstance(run_traffic, tuple):
                failed[vm] = run_traffic[1]
        if len(failed) > 0:
            self._log.info(
                "\nFollowing Traffic Test Failed After Applying TCP-ICMP-COMBO Contract == %s" % (failed))
            return 0
        else:
            return 1

    def test_6_traff_rem_prs(self):
        """
        Remove the PRS/Contract from the ExtPTG
        Test all traffic types
        """
        failed = []
        self._log.info("\nRemoving Prov/Cons contract from External PTG")
        for ext_pol in [self.external_pol_1, self.external_pol_2]:
            if self.gbpcrud.update_gbp_external_policy(ext_pol,
                                                        property_type='uuid',
                                                        provided_policy_rulesets=None,
                                                        consumed_policy_rulesets=None) == 0:
                return 0
        for vm in self.vmtuple:
            self._log.info(
                "\nTestcase_DNAT_%s_to_RESTOFVMs: CONTRACT REMOVED FROM ExtPTGs and VERIFY TRAFFIC" % (vm))
            run_traffic = self.nat_traffic.test_traff_from_vm_to_allvms(vm)
            if run_traffic == 2:
               self._log.error("\n Traffic VM %s Unreachable, Test = Aborted" %(vm))
               return 2
            if not isinstance(run_traffic, tuple):  # Negative check
                failed.append(vm)
        if len(failed) > 1:
            self._log.info(
                "\nFollowing Traffic Test with Contract removed from ExtPTG Failed for these Dest VMs = %s" % (failed))
            return 0
        else:
            return 1

    def cleanup(self):
           """
           This cleanup was need to avoid the failure
           in heat-delete. For some reason it complaints
           about the dependency b/w nat-pool & nsp
           """
           for vm in self.vmtuple:
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
 
