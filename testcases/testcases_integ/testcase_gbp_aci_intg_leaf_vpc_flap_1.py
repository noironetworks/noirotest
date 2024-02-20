#!/usr/bin/python

import sys
import logging
import os
import datetime
import string
from time import sleep
from libs.gbp_heat_libs import gbpHeat
from libs.raise_exceptions import *
from libs.gbp_aci_libs import Gbp_Aci
from libs.gbp_nova_libs import gbpNova
from libs.gbp_utils import *
from test_utils import *


class testcase_gbp_aci_intg_leaf_vpc_flap_1(object):
    """
    This is a GBP_ACI Integration TestCase
    """
    # Initialize logging
    #logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.setLevel(logging.INFO)
    # create a logfile handler
    hdlr = logging.FileHandler('/tmp/testcase_gbp_aci_intg_leaf_vpc_flap_1.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    hdlr.setFormatter(formatter)
    # Add the handler to the logger
    _log.addHandler(hdlr)

    def __init__(self,params):

      self.gbpaci = Gbp_Aci()
      self.heat_stack_name = 'gbpvpc1'
      cntlr_ip = params['cntlr_ip']
      self.heat_temp_test = params['heat_temp_file']
      self.gbpheat = gbpHeat(cntlr_ip)
      self.gbpnova = gbpNova(cntlr_ip)
      self.apic_ip = params['apic_ip']
      self.az_comp_node = params['az_comp_node']
      self.nova_agg = params['nova_agg']
      self.nova_az = params['nova_az']
      self.network_node = params['network_node']
      self.leaf1_port = params['leaf1_port1'] #This connects Leaf1 to Comp-node1
      self.leaf2_port = params['leaf2_port1'] #This connects Leaf2 to Comp-node1
      self.node1_id = params['leaf1_node_id']
      self.node2_id = params['leaf2_node_id']


    def test_runner(self):
        """
        Method to run the Testcase in Ordered Steps
        """
        test_name = 'VPC_DISCON_LEAF1&2_NODE1'
        self._log.info("\nSteps of the TESTCASE_GBP_INTG_LEAF_VPC_1_VPC_DISCON_LEAF1&2_NODE1 to be executed\n")
        testcase_steps = [self.test_step_SetUpConfig,
                          self.test_step_DisconnectLeaf1Host,
                          self.test_step_VerifyTraffic,
                          self.test_step_DisconnectLeaf2Host,
                          self.test_step_VerifyTraffic
                         ]
        status = ''
        for step in testcase_steps:
            if step()!=1:
                  self._log.info("Test Failed at Step == %s" %(step.__name__.lstrip('self')))
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
        print('Enable SSH .. sleeping for 20 secs')
        create_add_filter(self.apic_ip,'demo_bd') # 'demo_bd' is the name of L2Policy in the Heat Temp
        sleep(20)
        return 1

    def test_step_DisconnectLeaf1Host(self):
        """
        Test Step to Disconnect Leaf1 Port of vPC from Comp-node1
        """
        self._log.info("\nStep to Disconnect Link between Leaf1 and Comp-Node-1 in vPC\n")
        if self.gbpaci.enable_disable_switch_port(self.apic_ip,self.node1_id,'disable',self.leaf1_port) == 0:
           return 0
        return 1
 
    def test_step_DisconnectLeaf2Host(self):
        """
        Test Step to Disconnect Leaf2 Port from Comp-node1
        """
        self._log.info("\nStep to Disconnect Link between Leaf2 and Comp-Node-1 in vPC\n")
        # Before disabling Leaf2-CompNode1 link, ensure to enable Leaf1-CompNode1 link
        self.gbpaci.enable_disable_switch_port(self.apic_ip,self.node1_id,'enable',self.leaf1_port)
        print('\n Sleeping for 30 secs after enabling Leaf1-CompNode1 link')
        sleep(30)
        self._log.info("\nStep to Disconnect Link between Leaf2 and Comp-Node-1 in vPC\n")
        if self.gbpaci.enable_disable_switch_port(self.apic_ip,self.node2_id,'disable',self.leaf2_port) == 0:
           return 0
        return 1

    def test_step_VerifyTraffic(self):
        """
        Send and Verify traffic
        """
        self._log.info("\nSend and Verify Traffic\n")
        return verify_traff(self.network_node)

    def test_CleanUp(self):
        """
        Cleanup the Testcase setup
        """
        self._log.info("\nCleanUp to be executed\n")
        self.gbpaci.enable_disable_switch_port(self.apic_ip,self.node1_id,'enable',self.leaf1_port)
        self.gbpaci.enable_disable_switch_port(self.apic_ip,self.node2_id,'enable',self.leaf2_port)
        self.gbpnova.avail_zone('api','removehost',self.agg_id,hostname=self.az_comp_node)
        self.gbpnova.avail_zone('api','delete',self.agg_id)
        self.gbpheat.cfg_all_cli(0,self.heat_stack_name)
        #sys.exit(1)
