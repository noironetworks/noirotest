#!/usr/bin/env python

import logging
import yaml
import sys

from natfunctestmethod import *

class GbpNatFuncGlobalCfg(object):
    
    def CfgGlobalObjs(self):
        LOG.info(
            "\n## START OF GBP NAT FUNCTIONALITY TESTSUITE GLOBAL CONFIG\n")
        LOG.info(
               "\n## Create a Policy Action needed for NAT Testing ##")
        gbpcrud.create_gbp_policy_action(ACTION,
                                             action_type='allow')
        self.actid = gbpcrud.verify_gbp_policy_action(ACTION)
        if self.actid == 0:
            LOG.error(
                "\n## Reqd Policy Action Create Failed, hence GBP "
                "NAT Functional Test Suite Run ABORTED\n")
            LOG.info("\nCleaning Up")
            self.cleanup()            
            return 0
        
        LOG.info(
               '\n## Create a ICMP Policy Classifier needed for NAT Testing ##')
        gbpcrud.create_gbp_policy_classifier(CLSF_ICMP,
                                                  direction= 'bi',
                                                  protocol = 'icmp')
        self.clsicmpid = gbpcrud.verify_gbp_policy_classifier(CLSF_ICMP)
        if self.clsicmpid == 0:
            LOG.error(
                "\nReqd ICMP Policy Classifier Create Failed, hence GBP "
                "NAT Functional Test Suite Run ABORTED\n")
            LOG.info("\nCleaning Up")
            self.cleanup()
            return 0
        
        LOG.info(
               '\n## Create a ICMP Policy Rule needed for NAT Testing ##')
        gbpcrud.create_gbp_policy_rule(PR_ICMP,
                                            self.clsicmpid,
                                            self.actid,
                                            property_type = 'uuid')
        self.ruleicmpid = gbpcrud.verify_gbp_policy_rule(PR_ICMP)
        if self.ruleicmpid == 0:
            LOG.error(
                "\n## Reqd Policy Rule Create Failed, hence GBP NAT"
                " Functional Test Suite Run ABORTED\n ")
            LOG.info("\nCleaning Up")
            self.cleanup()
            return 0
        
        LOG.info(
               '\n## Create a TCP Policy Classifier needed for NAT Testing ##')
        gbpcrud.create_gbp_policy_classifier(CLSF_TCP,
                                                  direction= 'bi',
                                                  protocol = 'tcp',
                                                  port_range = '20:2000')
        self.clstcpid = gbpcrud.verify_gbp_policy_classifier(CLSF_TCP)
        if self.clstcpid == 0:
            LOG.error(
                "\nReqd TCP Policy Classifier Create Failed, hence GBP "
                "NAT Functional Test Suite Run ABORTED\n")
            LOG.info("\nCleaning Up")
            self.cleanup()
            return 0
        
        LOG.info(
               '\n## Create a TCP Policy Rule needed for NAT Testing ##')
        gbpcrud.create_gbp_policy_rule(PR_TCP,
                                            self.clstcpid,
                                            self.actid,
                                            property_type = 'uuid')
        self.ruletcpid = gbpcrud.verify_gbp_policy_rule(PR_TCP)
        if self.ruletcpid == 0:
            LOG.error(
                "\n## Reqd TCP Policy Rule Create Failed, hence GBP NAT"
                " Functional Test Suite Run ABORTED\n ")
            LOG.info("\nCleaning Up")
            self.cleanup()
            return 0
        
        LOG.info(
               '\n## Create a ICMP-TCP Policy Rule Set needed for NAT Testing ##')
        gbpcrud.create_gbp_policy_rule_set(
                                                PRS_ICMP_TCP,
                                                rule_list=[
                                                self.ruleicmpid,
                                                self.ruletcpid
                                                ],
                                        property_type = 'uuid')
        self.prsicmptcpid = gbpcrud.verify_gbp_policy_rule_set(PRS_ICMP_TCP)
        if self.prsicmptcpid == 0:
            LOG.error(
                "\n## Reqd ICMP-TCP Policy RuleSet Create Failed, hence "
                "GBP NAT Functional Test Suite "
                "Run ABORTED\n ")
            LOG.info("\nCleaning Up")
            self.cleanup()
            return 0

        LOG.info(
               '\n## Create a ICMP Policy Rule Set needed for NAT Testing ##')
        gbpcrud.create_gbp_policy_rule_set(
                                        PRS_ICMP,
                                        rule_list=[self.ruleicmpid],
                                        property_type = 'uuid'
                                        )
        self.prsicmpid = gbpcrud.verify_gbp_policy_rule_set(PRS_ICMP)
        if self.prsicmpid == 0:
            LOG.error(
                "\n## Reqd ICMP Policy RuleSet Create Failed, hence "
                "GBP NAT Functional Test Suite "
                "Run ABORTED\n ")
            LOG.info("\nCleaning Up")
            self.cleanup()
            return 0

        LOG.info(
               '\n## Create a TCP Policy Rule Set needed for NAT Testing ##')
        gbpcrud.create_gbp_policy_rule_set(
                                        PRS_TCP,
                                        rule_list=[self.ruletcpid],
                                        property_type = 'uuid'
                                        )
        self.prstcpid = gbpcrud.verify_gbp_policy_rule_set(PRS_TCP)
        if self.prstcpid == 0:
            LOG.error(
                "\n## Reqd TCP Policy RuleSet Create Failed, hence "
                "GBP NAT Functional Test Suite "
                "Run ABORTED\n ")
            LOG.info("\nCleaning Up")
            self.cleanup()
            return 0

    def add_avail_zone(self):
            try:
               # Check if Agg already exists then delete
               cmdagg = run_openstack_cli("nova aggregate-list", CNTRLRIP)
               if NOVA_AGG in cmdagg:
                  LOG.warning("Residual Nova Agg exits, hence deleting it")
                  gbpnova.avail_zone('cli', 'removehost',
                                           NOVA_AGG,
                                           hostname=AZ_COMP_NODE)
                  gbpnova.avail_zone('cli', 'delete', NOVA_AGG)
               LOG.info("\nCreating Nova Host-aggregate & its Availability-zone")
               self.agg_id = gbpnova.avail_zone(
                       'api', 'create', NOVA_AGG, avail_zone_name=AVAIL_ZONE)
            except Exception:
                LOG.error(
                    "\n ABORTING THE TESTSUITE RUN,nova host aggregate creation Failed", exc_info=True)
                sys.exit(1)
            LOG.info(" Agg %s" % (self.agg_id))
            try:
             LOG.info("\nAdding Nova host to availaibility-zone")
             gbpnova.avail_zone('api', 'addhost', self.agg_id, hostname=AZ_COMP_NODE)
            except Exception:
                LOG.error(
                    "\n ABORTING THE TESTSUITE RUN, availability zone creation Failed", exc_info=True)
                gbpnova.avail_zone(
                    'cli', 'delete', self.agg_id)  # Cleanup Agg_ID
                sys.exit(1)


    def cleanup(self):
        # cleanup the resources created by a testcase(Blind Cleanup)
        LOG.info("\nGlobal Config Clean-Up Initiated")
        prs_list = gbpcrud.get_gbp_policy_rule_set_list()
        if len(prs_list) > 0:
           for prs in prs_list:
               gbpcrud.delete_gbp_policy_rule_set(prs, property_type='uuid')
        pr_list = gbpcrud.get_gbp_policy_rule_list()
        if len(pr_list) > 0:
           for pr in pr_list:
               gbpcrud.delete_gbp_policy_rule(pr, property_type='uuid')
        cls_list = gbpcrud.get_gbp_policy_classifier_list()
        if len(cls_list) > 0:
           for cls in cls_list:
               gbpcrud.delete_gbp_policy_classifier(cls, property_type='uuid')
        act_list = gbpcrud.get_gbp_policy_action_list()
        if len(act_list) > 0:
           for act in act_list:
               gbpcrud.delete_gbp_policy_action(act, property_type='uuid')
	if PLUGIN_TYPE:
	    for l3out in [EXTSEG_PRI, EXTSEG_SEC]:
	 	neutron.runcmd('neutron net-delete %s' %(l3out))
        LOG.info("\nGlobal Config Clean-Up Completed")

    
