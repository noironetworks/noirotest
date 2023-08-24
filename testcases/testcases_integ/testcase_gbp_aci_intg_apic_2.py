#!/usr/bin/python

import sys
import logging
import os
import datetime
import yaml
import string
from time import sleep
from libs.gbp_conf_libs import gbpCfgCli
from libs.gbp_verify_libs import Gbp_Verify
from libs.gbp_fab_traff_libs import Gbp_def_traff
from libs.gbp_pexp_traff_libs import Gbp_pexp_traff
from libs.gbp_heat_libs import gbpHeat
from libs.raise_exceptions import *
from libs.gbp_aci_libs import Gbp_Aci
from libs.gbp_utils import *
from test_utils import *


class  testcase_gbp_aci_intg_apic_2(object):
    """
    This is a GBP_ACI Integration TestCase
    """
    # Initialize logging
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
    _log = logging.getLogger( __name__ )
    hdlr = logging.FileHandler('/tmp/testcase_gbp_aci_intg_apic_2.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    _log.addHandler(hdlr)
    _log.setLevel(logging.INFO)
    _log.setLevel(logging.DEBUG)

    def __init__(self,params):

      self.gbpcfg = gbpCfgCli()
      self.gbpverify = Gbp_Verify()
      self.gbpdeftraff = Gbp_def_traff()
      self.gbpaci = Gbp_Aci()
      self.heat_stack_name = 'gbpapic3'
      self.cntlr_ip = params['cntlr_ip']
      self.heat_temp_test = params['heat_temp_file']
      self.gbpheat = gbpHeat(self.cntlr_ip)
      self.gbpnova = gbpNova(self.cntlr_ip)
      self.leaf_ip = params['leaf1_ip']
      self.apic_ip = params['apic_ip']
      self.network_node = params['network_node']
      self.az_comp_node = params['az_comp_node']
      self.nova_agg = params['nova_agg']
      self.nova_az = params['nova_az']
      self.debug = param['pausetodebug']

      self.test_name = 'DISCONN_APIC_UPDATECFG_RECONN_APIC'
      self._log.info("\nSteps of the TESTCASE_GBP_INTG_APIC_2_DISCONN_APIC_UPDATECFG_RECONN_APIC to be executed\n")
      if self.test_step_SetUpConfig()!=1:
           self._log.info("Test Failed at Step_1 == SetUpConfig")
           self.test_CleanUp()
      if self.test_step_VerifyTraffic() != 1:
           self._log.info("Test Failed at Step_2 == TestVerifyTraffic")
           self.test_CleanUp()
      objs_uuid = self.gbpverify.get_uuid_from_stack(self.heat_temp_test,self.heat_stack_name)
      self.ptg_1 = objs_uuid['server_ptg_id']
      self.ptg_2 = objs_uuid['client_ptg_id']
      self.test_1_prs = objs_uuid['demo_ruleset_icmp_id']
      self.test_2_prs = objs_uuid['demo_ruleset_tcp_id']
      self.test_3_prs = objs_uuid['demo_ruleset_udp_id']
      self.test_4_prs = objs_uuid['demo_ruleset_icmp_tcp_id']
      self.test_5_prs = objs_uuid['demo_ruleset_icmp_udp_id']
      self.test_6_prs = objs_uuid['demo_ruleset_tcp_udp_id']
      self.prs_proto = {self.test_1_prs:['icmp'],self.test_2_prs:['tcp'],self.test_3_prs:['udp'],\
                   self.test_4_prs:['icmp','tcp'],self.test_5_prs:['icmp','udp'],self.test_6_prs:['tcp','udp']}

    def test_runner(self):
        """
        Method to run the Testcase in Ordered Steps
        """
        testcase_steps = [self.test_step_DisconnectApic,
                              self.test_step_UpdatePtg,
                              self.test_step_ReconnectApic,
                              self.test_step_RestartNeutron,
                              self.test_step_VerifyTraffic]
        status = ''
        for prs,proto in self.prs_proto.items():
            for step in testcase_steps: 
                if step == 'self.test_step_VerifyTraffic':
                   if step(proto) != 1:
                      self._log.info("Test Failed at Step == VerifyTraffic for Protocol = %s" %(proto))
                      self._log.info("%s_%s == FAILED" %(self.__class__.__name__.upper(),self.test_name))
                      status = 'failed'
                      break
                   elif step()!=1:
                      self._log.info("Test Failed at Step == %s" %(step.__name__.lstrip('self')))
                      self._log.info("%s_%s == FAILED" %(self.__class__.__name__.upper(),self.test_name))
                      status = 'failed'
                      break
            if status == 'failed':
               if self.debug == True:
                     PauseToDebug()
               break
        if status != 'failed':
           self._log.info("%s_%s == PASSED" %(self.__class__.__name__.upper(),self.test_name))
        self.test_CleanUp()

    def test_step_SetUpConfig(self):
        """
        Test Step using Heat, setup the Test Config
        """
        self.agg_id = self.gbpnova.avail_zone('api','create',self.nova_agg,avail_zone_name=self.nova_az)
        if self.agg_id == 0:
            self._log.info("\n ABORTING THE TESTSUITE RUN,nova host aggregate creation Failed")
            sys.exit(1)
        self._log.info(" Agg %s" %(self.agg_id))
        if self.gbpnova.avail_zone('api','addhost',self.agg_id,hostname=self.az_comp_node) == 0:
            self._log.info("\n ABORTING THE TESTSUITE RUN, availability zone creation Failed")
            self.gbpnova.avail_zone('api','delete',self.nova_agg,avail_zone_name=self.nova_az) # Cleaning up
            sys.exit(1)
        sleep(3)
        if self.gbpheat.cfg_all_cli(1,self.heat_stack_name,heat_temp=self.heat_temp_test) == 0:
           self._log.info("\n ABORTING THE TESTSUITE RUN, HEAT STACK CREATE of %s Failed" %(self.heat_stack_name))
           self.test_CleanUp()
           sys.exit(1)
        print('Enable SSH .. sleeping for 20 secs')
        create_add_filter(self.apic_ip,'demo_bd') # 'demo_bd' is the name of L2Policy in the Heat Temp
        sleep(20)
        return 1

    def test_step_UpdatePtg(self,prs):
        """
        Update the PTG with new PRS & Restart the Neutron-Server
        """
        if self.gbpcfg.gbp_policy_cfg_all(2,'group',self.ptg_1,provided_policy_rule_sets="%s=scope" %(prs))\
           and self.gbpcfg.gbp_policy_cfg_all(2,'group',self.ptg_2,consumed_policy_rule_sets="%s=scope" %(prs))==0:
           self._log.info("Updating PTG = Failed")
           return 0

    def test_step_RestartNeutron(self):
        getoutput('systemctl restart neutron-server.service')
        sleep(5)
        return 1

    def test_step_DisconnectApic(self):
        """
        Test Step to Disconnect APIC from Ostack Controller
        """
        if self.gbpaci.dev_conn_disconn(self.cntlr_ip,self.apic_ip,'disconnect') == 0:
           return 0
        return 1
 
    def test_step_VerifyObjsApic(self):
        """
        Test Step to verify that all configured objs are available in APIC
        """
        if self.gbpaci.apic_verify_mos(self.apic_ip) == 0:
           return 0
        return 1

    def test_step_ReconnectApic(self):
        """
        Test Step to Reconnect APIC to Ostack Controller
        """
        if self.gbpaci.dev_conn_disconn(self.cntlr_ip,self.apic_ip,'reconnect') == 0:
           return 0
        return 1

    def test_step_VerifyTraffic(self,proto='all'):
        """
        Send and Verify traffic
        """
        return verify_traff(self.network_node)

    def test_CleanUp(self):
        """
        Cleanup the Testcase setup
        """
        self.gbpaci.dev_conn_disconn(self.cntlr_ip,self.apic_ip,'reconnect')
        self.gbpnova.avail_zone('api','removehost',self.agg_id,hostname=self.az_comp_node)
        self.gbpnova.avail_zone('api','delete',self.agg_id)
        self.gbpheat.cfg_all_cli(0,self.heat_stack_name)
        #sys.exit(1)

