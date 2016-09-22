#!/usr/bin/env python
import sys
import optparse
from commands import *
getoutput("rm -rf /tmp/test*") #Deletes pre-existing test logs
from time import sleep
from libs.gbp_verify_libs import Gbp_Verify
from libs.gbp_utils import *
from natdptestsetup import nat_dp_main_config

def get_obj_uuids(cfgfile,nat_type=''):

    gbpverify = Gbp_Verify()
    testbed_cfg = nat_dp_main_config(cfgfile)
    if nat_type == '' or nat_type == 'dnat':
       objs_uuid = gbpverify.get_uuid_from_stack(
                    testbed_cfg.dnat_heat_temp,
                    testbed_cfg.heat_stack_name
                    )
    if nat_type == 'snat':
       objs_uuid = gbpverify.get_uuid_from_stack(
                    testbed_cfg.snat_heat_temp,
                    testbed_cfg.heat_stack_name
                    )
    objs_uuid['external_gw'] = testbed_cfg.extgw
    objs_uuid['ostack_controller'] = testbed_cfg.cntlr_ip
    objs_uuid['ipsofextgw'] = testbed_cfg.ips_of_extgw
    objs_uuid['ntk_node'] = testbed_cfg.ntk_node
    objs_uuid['pausetodebug'] = testbed_cfg.pausetodebug
    print 'OBJS_UUID == \n', objs_uuid
    return objs_uuid

def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-c", "--configfile",
                      help="Mandatory Arg: Name of the Config File with location",
                      dest='configfile')
    parser.add_option("-o", "--controllerIp",
                      help="Mandatory Arg: IP Address of the Ostack Controller",
                      dest='cntlrIp')
    parser.add_option("-n", "--nattype",
                      help="Mandatory Arg: Type of NAT"\
                      " Valid strings: dnat or snat or edgenat",
                      dest='nattype')
    parser.add_option("-p", "--ptnepg",
                      help="Flag to enable Per Tenant NAT-EPG"\
                      " Valid string: <yes>",
                      default=False,
                      dest='pertenantnatepg')
    parser.add_option("-i", "--integ",
                      help="integrated ACI Tests. "\
                      "Valid strings: borderleaf or leaf or spine or agent",
                      default=False,
                      dest='integ')
    (options, args) = parser.parse_args()

    if not options.configfile:
        print ("Mandatory: Please provide the ConfigFile with location")
        sys.exit(1)
    if not options.cntlrIp:
        print ("Mandatory: Please provide the Ostack Controller IP")
        sys.exit(1)
    if not options.nattype:
        print ("Mandatory: Please provide the NAT-Type, "\
               "Valid strings <dnat> or <snat> or <edgenat>")
        sys.exit(1)
    def runinteg(node):
        if node == 'borderleaf':
                print "////// Run DP-Test Post Reload of BorderLeaf //////"
                reboot = 'POST_RELOAD_BORDERLEAF'
                testbed_cfg.reloadAci()
        if node == 'leaf':
                print "////// Run DP-Test Post Reload of Non-BorderLeaf //////"
                reboot = 'POST_RELOAD_NONBORDERLEAF'
                testbed_cfg.reloadAci(nodetype='leaf')
        if node == 'spine':
                print "////// Run DP-Test Post Reload of Spine //////"
                reboot = 'POST_RELOAD_SPINE'
                testbed_cfg.reloadAci(nodetype='leaf')
                print " **** Sleeping for Spine toboot up ****"
                sleep(430)  
        if node == 'agent':
                print "////// Run DP-Test Post Reload of Agent //////"
                reboot = 'AGENT_RESTART'
                testbed_cfg.restartAgent()
                print " **** Sleeping for 5s after Agent Restart ****"
                sleep(5)
       
    def preExistcfg(controller,nat_type='',revert=False):
        if not revert:
            if nat_type == 'edgenat':
                preExistingL3Out(controller,
                         '/etc/neutron/neutron.conf',
                         edgenat=True
                         )
            else:
                preExistingL3Out(controller,
                         '/etc/neutron/neutron.conf'
                         )
        else:
            preExistingL3Out(controller,
                    '/etc/neutron/neutron.conf',
                    revert=True
                         )
                
    # Setup the PreExitingL3Out Config in neutron conf
    preExistcfg(options.cntlrIp)
    # Build the Test Config to be used for all NAT DataPath Testcases
    cfgfile = options.configfile
    nat_type = options.nattype
    testbed_cfg = nat_dp_main_config(cfgfile)
    if nat_type == 'dnat':
        # RUN ONLY DNAT DP TESTs
        # TestSetup Configuration
        print 'Setting up global config for all DNAT DP Testing'
	if options.pertenantnatepg:
            print 'Test for PER_TENANT_NAT_EPG FOR DNAT'
            targetVmFips = testbed_cfg.setup(
					     nat_type,
                                             do_config=0,
					     pertntnatEpg=True
					     )
	else:
	    targetVmFips = testbed_cfg.setup(
					     nat_type,
					     do_config=0
					     )
        # Fetch gbp objects via heat output
        objs_uuid = get_obj_uuids(cfgfile)
        # Verify the config setup on the ACI
	print 'Sleeping for the EP learning on ACI Fab'
	sleep(30)   
	if options.pertenantnatepg:
	    if not testbed_cfg.verifySetup(nat_type,
                                           pertntnatEpg=True):
	        testbed_cfg.cleanup()
                preExistcfg(options.cntlrIp,revert=True)
	        print \
                'DNAT-PerTntNatEpg TestSuite Execution Failed'
                sys.exit(1)
	else:
	    if not testbed_cfg.verifySetup(nat_type):
	        testbed_cfg.cleanup()
                preExistcfg(options.cntlrIp,revert=True)
	        print \
                'DNAT TestSuite Execution Failed'
                sys.exit(1)
        # Note: Please always maintain the below order of DNAT Test Execution
        # Since the DNAT_VM_to_VM has the final blind cleanup, which helps to
        # avoid the heat stack-delete failure coming from nat_dp_main_config
        
        # Execution of DNAT DP Tests from ExtRtr to VMs
        from testcases.testcases_dp_nat.testsuite_dnat_extgw_to_vm \
        import DNAT_ExtGw_to_VMs
        test_dnat_extgw_to_vm = DNAT_ExtGw_to_VMs(objs_uuid,
						 targetVmFips)
        test_dnat_extgw_to_vm.test_runner()
        if options.integ:
           #Only run ExtRtr-VM Tests, no need for VM-to-VM, will enable
           #if needed later
           runinteg(options.integ)
           if testbed_cfg.verifySetup(nat_type):
              testbed_cfg.cleanup()
              #Revert Back the L3Out Config
              preExistcfg(options.cntlrIp,revert=True)
              print \
                  'DNAT-Integ TestSuite Execution Failed after Reload %s'\
                  %(options.integ)
              sys.exit(1)
           test_dnat_extgw_to_vm.test_runner()
           # Cleanup
           testbed_cfg.cleanup()
           print "\nDNAT-Integ TestSuite executed Successfully\n"
           sys.exit(1) # No need to run VM-toVM with ACI-Integ
        # Execution of DNAT DP Test from VM to ExtGW and VM-to-VM    
        from testcases.testcases_dp_nat.testsuite_dnat_vm_to_vm \
        import DNAT_VMs_to_VMs
        test_dnat_vm_to_allvms = DNAT_VMs_to_VMs(objs_uuid, targetVmFips)
        test_dnat_vm_to_allvms.test_runner()
        # Cleanup
        testbed_cfg.cleanup()
        print "\nDNAT TestSuite executed Successfully\n"
        
    if nat_type == 'snat':
        # RUN ONLY SNAT DP TESTs
        # TestSetup Configuration
        print 'Setting up global config for SNAT DP Testing'
        testbed_cfg.setup('snat', do_config=0)
        # Fetch gbp objects via heat output
        objs_uuid = get_obj_uuids(cfgfile)
        # Verify the config setup on the ACI
	print 'Sleeping for the EP learning on ACI Fab'
	sleep(30)   
	if not testbed_cfg.verifySetup(nat_type):
	    testbed_cfg.cleanup()
            preExistcfg(options.cntlrIp,revert=True)
	    print 'SNAT TestSuite Execution Failed due to Setup Issue'
            sys.exit(1)
        # Execution of SNAT DP Tests
        from testcases.testcases_dp_nat.testsuite_snat_vm_to_extgw \
        import SNAT_VMs_to_ExtGw
        test_snat_allvms_to_extgw = SNAT_VMs_to_ExtGw(objs_uuid)
        test_snat_allvms_to_extgw.test_runner()
        if options.integ:
           #Only Run ExtRtr-VM Tests, no need for VM-to-VM, will enable
           #if needed later
           runinteg(options.integ)
           if testbed_cfg.verifySetup(nat_type):
              testbed_cfg.cleanup()
              preExistcfg(options.cntlrIp,revert=True)
              print \
                  'SNAT-Integ TestSuite Execution Failed after Reload %s'\
                  %(options.integ)
              sys.exit(1)
           test_dnat_extgw_to_vm.test_runner()
        # Cleanup after the SNAT Testsuite is run
        testbed_cfg.cleanup()
        print "\nSNAT TestSuite executed Successfully\n"
    #Revert Back the L3Out Config
    preExistcfg(options.cntlrIp,revert=True)

if __name__ == "__main__":
    main()
