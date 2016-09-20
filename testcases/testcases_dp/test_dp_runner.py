#!/usr/bin/env python
import os
import sys
import optparse
import platform
from commands import *
getoutput("rm -rf /tmp/test*") #Deletes pre-existing test logs
from time import sleep
from libs.gbp_verify_libs import Gbp_Verify
from test_main_config import gbp_main_config
from testcases.testcases_dp.testsuites_setup_cleanup import super_hdr, header1, header2, header3, header4
from testcases.testcases_dp.testsuite_same_ptg_l2p_l3p import test_same_ptg_same_l2p_same_l3p
from testcases.testcases_dp.testsuite_diff_ptg_same_l2p_l3p import test_diff_ptg_same_l2p_l3p
from testcases.testcases_dp.testsuite_diff_ptg_diff_l2p_same_l3p import test_diff_ptg_diff_l2p_same_l3p
from testcases.testcases_dp.testsuite_diff_ptg_diff_l2p_diff_l3p import test_diff_ptg_diff_l2p_diff_l3p


def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-c", "--configfile",
                      help="Name of the Config File with location",
                      dest='configfile')
    parser.add_option("-i", "--integ",
                      help="integrated ACI tests"\
                      "valid strings: borderleaf or leaf or spine or agent",
                      default=False,
                      dest='integ')
    (options, args) = parser.parse_args()

    if options.configfile == None:
        print "Please provide the ConfigFile with location"
        sys.exit(1)
    else:
        # Build the Test Config to be used for all DataPath Testcases
        print "Setting up global config for all DP Testing"
        testbed_cfg = gbp_main_config(options.configfile)
        testbed_cfg.setup()

        # Fetch gbp objects via heat output
        gbpverify = Gbp_Verify()
        objs_uuid = gbpverify.get_uuid_from_stack(
            super_hdr.heat_temp, super_hdr.stack_name)

        # Verify the configuration on ACI
        print "Verification .. sleep 30s, allowing DP learning"
        sleep(30)
        if not testbed_cfg.verifySetup():
            testbed_cfg.cleanup()
            sys.exit(1)

    header_to_suite_map = {'header1': [header1, test_same_ptg_same_l2p_same_l3p],
                           'header2': [header2, test_diff_ptg_same_l2p_l3p],
                            'header3': [header3, test_diff_ptg_diff_l2p_same_l3p],
                           'header4': [header4, test_diff_ptg_diff_l2p_diff_l3p]}
 
    def run(reboot=''):
        for val in header_to_suite_map.itervalues():
            # Initialize Testsuite specific config setup/cleanup class
            header = val[0]()
            # Build the Testsuite specific setup/config
            # header.setup()

            # Initialize Testsuite class to run its testcases
            testsuite = val[1](objs_uuid)
            for location in ['same_host', 'diff_host_diff_leaf']:
                if reboot:
                    log_string = "%s_%s_%s_%s_%s" % (
                              testbed_cfg.test_parameters['bd_type'],
                              testbed_cfg.test_parameters['ip_version'],
                              testbed_cfg.test_parameters['vpc_type'],
                              location,
                              reboot)
                else:
                    log_string = "%s_%s_%s_%s" % (
                              testbed_cfg.test_parameters['bd_type'],
                              testbed_cfg.test_parameters['ip_version'],
                              testbed_cfg.test_parameters['vpc_type'],
                              location)
                testsuite.test_runner(log_string, location)
        # now run the loop of test-combos(NOTE: The below forloop is now part of Harness & cfgable)
        """
        for bdtype in ['vxlan', 'vlan']:
            for ip in ['ipv4', 'ipv6']:
                for vpc in ['novpc', 'vpc_novpc', 'vpc_vpc']:
                    for location in ['same_host', 'diff_host_same_leaf', 'diff_host_diff_leaf']:
                        # Run the testcases specific to the initialized
                        # testsuite
                        log_string = "%s_%s_%s_%s" % (
                            bdtype, ip, vpc, location)
                        testsuite.test_runner(log_string, location)
        """
    run() #Run the Test without any Integration Test, this will ALWAYS RUN

    # Options to Run ACI Integration Tests:
    if options.integ:
        #With VPC if any of the Leafs reboot, then traffic should be 
        #able to flow through the other Leaf. Only in case of Spine
        #we should sleep 7 mins before we send traffic
        #TODO: Add online status check for the leafs/spines post reload
        if options.integ == 'borderleaf':
                print "////// Run DP-Test Post Reload of BorderLeaf //////"
                reboot = 'POST_RELOAD_BORDERLEAF'
                testbed_cfg.reloadAci()
        if options.integ == 'leaf':
                print "////// Run DP-Test Post Reload of Non-BorderLeaf //////"
                reboot = 'POST_RELOAD_NONBORDERLEAF'
                testbed_cfg.reloadAci(nodetype='leaf')
        if options.integ == 'spine':
                print "////// Run DP-Test Post Reload of Spine //////"
                reboot = 'POST_RELOAD_SPINE'
                testbed_cfg.reloadAci(nodetype='leaf')
                print " **** Sleeping for Spine toboot up ****"
                sleep(430)  
        # After Reboot of ACI node, verifyCfg and send traffic
        if not testbed_cfg.verifySetup():
                print "Verification of Test Config Failed, %s" %(reboot)
                testbed_cfg.cleanup()
                sys.exit(1)
	run(reboot)
    testbed_cfg.cleanup() 
    print "\nDataPath TestSuite executed Successfully\n"

if __name__ == "__main__":
    main()
