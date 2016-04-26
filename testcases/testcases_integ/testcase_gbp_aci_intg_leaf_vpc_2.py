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


class testcase_gbp_aci_intg_leaf_vpc_2(object):
    """
    This is a GBP_ACI Integration TestCase
    """
    # Initialize logging
    #logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.setLevel(logging.INFO)
    # create a logfile handler
    hdlr = logging.FileHandler('/tmp/testcase_gbp_aci_intg_leaf_vpc_2.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    hdlr.setFormatter(formatter)
    # Add the handler to the logger
    _log.addHandler(hdlr)

    def __init__(self,params):

      self.gbpaci = Gbp_Aci()
      self.heat_stack_name = 'gbpvpc1'
      cntlr_ip = params['cntlr_ip']
      self.heat_temp_test = params['heat_temp_file']
      self.gbpheat = Gbp_Heat(cntlr_ip)
      self.gbpnova = Gbp_Nova(cntlr_ip)
      self.apic_ip = params['apic_ip']
      self.az_comp_node = params['az_comp_node']
      self.nova_agg = params['nova_agg']
      self.nova_az = params['nova_az']
      self.ntk_node = params['ntk_node']
      self.leaf2_ip = params['leaf2_ip']
      self.leafname = params['leaf2name']
      self.debug = params['pausetodebug']

    def test_runner(self):
        """
        Method to run the Testcase in Ordered Steps
        """
        test_name = 'REBOOT_LEAF2'
        self._log.info("\nSteps of the TESTCASE_GBP_INTG_LEAF_VPC_2_REBOOT_LEAF2 to be executed\n")
        testcase_steps = [self.test_step_SetUpConfig,
                          self.test_step_RebootLeaf,
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

    def test_step_RebootLeaf(self):
        """
        Test Step to Reboot Leaf1
        """
        self._log.info("\nStep to Reboot Leaf2 in vPC\n")
        if self.gbpaci.reboot_aci(self.leaf2_ip) == 0:
           return 0
        sleep(10) #For reboot to kick-in
        return 1

    def test_step_VerifyTraffic(self):
        """
        Send and Verify traffic while one of the Leaf is booting up
        """
        self._log.info("\nSend and Verify Traffic\n")
        return verify_traff(self.ntk_node)

    def test_step_VerifyLeafTraffic(self):
        """
        Verify Leaf status as Active
        Send and Verify Traffic Again
        """
        print '\nSleep for every 20s and probe for Leaf become Active'
        while True:
              if self.gbpaci.aciStatus(self.apic_ip,self.leafname):
                 break
              else:
                  sleep(20)
        self._log.info("\nSend and Verify Traffic as Leaf has become Active Post-Reboot\n")
        return verify_traff(self.ntk_node)

    def test_CleanUp(self):
        """
        Cleanup the Testcase setup
        """
        self._log.info("\nCleanUp to be executed\n")
        self.gbpnova.avail_zone('api','removehost',self.agg_id,hostname=self.az_comp_node)
        self.gbpnova.avail_zone('api','delete',self.agg_id)
        self.gbpheat.cfg_all_cli(0,self.heat_stack_name)
        #sys.exit(1)
