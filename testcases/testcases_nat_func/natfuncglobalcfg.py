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
	 	neutron.runcmd('gbp purge %s' %(ADMIN_TNTID))
        else:
            nets = neutron.runcmd("neutron net-list -F name -f value")
            for net in nets:
                if net.startswith("apic_owned_"):
                    neutron.runcmd('neutron net-delete %s' %(net))

        LOG.info("\nGlobal Config Clean-Up Completed")

    
