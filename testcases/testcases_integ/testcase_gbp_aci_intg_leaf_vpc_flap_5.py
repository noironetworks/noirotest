#!/usr/bin/python

import sys
import logging
import os
import datetime
import string
from time import sleep
from libs.gbp_heat_libs import Gbp_Heat
from libs.raise_exceptions import *
from libs.gbp_aci_libs import Gbp_Aci
from libs.gbp_nova_libs import Gbp_Nova
from libs.gbp_utils import *
from test_utils import *


class testcase_gbp_aci_intg_leaf_vpc_flap_5(object):
    """
    This is a GBP_ACI Integration TestCase
    """

    # Initialize logging
    #logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.setLevel(logging.INFO)
    # create a logfile handler
    hdlr = logging.FileHandler('/tmp/testcase_gbp_aci_intg_leaf_vpc_flap_5.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    hdlr.setFormatter(formatter)
    # Add the handler to the logger
    _log.addHandler(hdlr)

    def __init__(self,params):

      self.gbpaci = Gbp_Aci()
      self.heat_stack_name = 'gbpvpc7'
      cntlr_ip = params['cntlr_ip']
      self.heat_temp_test = params['heat_temp_file']
      self.gbpheat = Gbp_Heat(cntlr_ip)
      self.gbpnova = Gbp_Nova(cntlr_ip)
      self.apic_ip = params['apic_ip']
      self.az_comp_node = params['az_comp_node']
      self.nova_agg = params['nova_agg']
      self.nova_az = params['nova_az']
      self.ntk_node = params['ntk_node']
      self.leaf1_port_comp_node1 = params['leaf1_port1'] #This connects Leaf1 to Comp-node1
      self.leaf2_port_comp_node2 = params['leaf2_port2'] #This connects Leaf2 to Comp-node2
      self.leaf1_node_id = params['leaf1_node_id']
      self.leaf2_node_id = params['leaf2_node_id']
      self.debug = params['pausetodebug']


    def test_runner(self):
        """
        Method to run the Testcase in Ordered Steps
        """
        test_name = 'VPC_DISCON_LEAF1_NODE1_LEAF2_NODE2'
        self._log.info("\nSteps of the TESTCASE_GBP_INTG_LEAF_VPC_5_VPC_DISCON_LEAF1_NODE1_LEAF2_NODE2 to be executed\n")
        testcase_steps = [self.test_step_SetUpConfig,
                          self.test_step_DisconnectLeafsFromHosts,
                          self.test_step_VerifyTraffic
                         ]
        status = ''
        for step in testcase_steps:
            if step()!=1:
                  self._log.info("Test Failed at Step == %s" %(step.__name__.lstrip('self')))
                  if self.debug == True:
                     PauseToDebug()
                  self._log.info("%s_%s == FAILED" %(self.__class__.__name__.upper(),test_name))        
                  status = 'failed'
                  break
        if status != 'failed':
           self._log.info("%s_%s == PASSED" %(self.__class__.__name__.upper(),test_name))        
        self.test_CleanUp()

    def test_step_SetUpConfig(self):
        """
        Test Step using Heat, setup the Test Config
        """
        self._log.info("\nSetupCfg: Create Aggregate & Availability Zone to be executed\n")
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
        print 'Enable SSH .. sleeping for 20 secs'
        create_add_filter(self.apic_ip,'demo_bd') # 'demo_bd' is the name of L2Policy in the Heat Temp
        sleep(20)
        return 1

    def test_step_DisconnectLeafsFromHosts(self):
        """
        Test Step to Disconnect Links b/w Leaf1-CompNode1,Leaf2-CompNode2
        """
        self._log.info("\nStep to Disconnect Links b/w Leaf1-CompNode1,Leaf2-CompNode2\n")
        if self.gbpaci.enable_disable_switch_port(self.apic_ip,self.leaf1_node_id,'disable',self.leaf1_port_comp_node1) == 0:
           return 0
        if self.gbpaci.enable_disable_switch_port(self.apic_ip,self.leaf2_node_id,'disable',self.leaf2_port_comp_node2) == 0:
           return 0
        return 1
 
    def test_step_VerifyTraffic(self):
        """
        Send and Verify traffic
        """
        self._log.info("\nSend and Verify Traffic\n")
        return verify_traff(self.ntk_node)

    def test_CleanUp(self):
        """
        Cleanup the Testcase setup
        """
        self._log.info("\nCleanUp to be executed\n")
        self.gbpaci.enable_disable_switch_port(self.apic_ip,self.leaf1_node_id,'enable',self.leaf1_port_comp_node1)
        self.gbpaci.enable_disable_switch_port(self.apic_ip,self.leaf2_node_id,'enable',self.leaf2_port_comp_node2)
        self.gbpnova.avail_zone('api','removehost',self.agg_id,hostname=self.az_comp_node)
        self.gbpnova.avail_zone('api','delete',self.agg_id)
        self.gbpheat.cfg_all_cli(0,self.heat_stack_name)
        #sys.exit(1)
