#!/usr/bin/env python
import sys
import optparse
from subprocess import *
getoutput("rm -rf /tmp/testsuite*") #Deletes pre-existing test logs
from time import sleep
from libs.gbp_heat_libs import gbpHeat
from libs.gbp_utils import *
from natdptestsetup import *

def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-n", "--nattype",
                      help="Mandatory Arg: Type of NAT"\
                      " Valid strings: dnat or snat or edgenat",
                      dest='nattype')
    parser.add_option("-f", "--ptnepg",
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

    if not options.nattype:
        print ("Mandatory: Please provide the NAT-Type, "\
               "Valid strings <dnat> or <snat> or <edgenat>")
        sys.exit(1)
    def runinteg(node):
        if node == 'borderleaf':
                print("////// Run DP-Test Post Reload of BorderLeaf //////")
                reboot = 'POST_RELOAD_BORDERLEAF'
                testbed_cfg.reloadAci()
        if node == 'leaf':
                print("////// Run DP-Test Post Reload of Non-BorderLeaf //////")
                reboot = 'POST_RELOAD_NONBORDERLEAF'
                testbed_cfg.reloadAci(nodetype='leaf')
        if node == 'spine':
                print("////// Run DP-Test Post Reload of Spine //////")
                reboot = 'POST_RELOAD_SPINE'
                testbed_cfg.reloadAci(nodetype='leaf')
                print(" **** Sleeping for Spine toboot up ****")
                sleep(430)  
        if node == 'agent':
                print("////// Run DP-Test Post Reload of Agent //////")
                reboot = 'AGENT_RESTART'
                testbed_cfg.restartAgent()
                print(" **** Sleeping for 5s after Agent Restart ****")
                sleep(5)
       
    def preExistcfg(controller,nat_type='',revert=False,restart=True):
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
                    revert=True,
                    restart=restart
                         )
    preexist = True #Going forward for all releases Pre-Existing L3Out
    nat_type = options.nattype
    if options.pertenantnatepg == 'yes':
       options.pertenantnatepg = True
    # Setup the PreExitingL3Out Config in neutron conf
    preExistcfg(cntlr_ip)
    # Build the Test Config to be used for all NAT DataPath Testcases
    testbed_cfg = nat_dp_main_config()
    gbpheat = gbpHeat(cntlr_ip) #Instantiated to fetch gbp-objects

    if nat_type == 'dnat':
        # RUN ONLY DNAT DP TESTs
        # TestSetup Configuration
        print('Setting up global config for all DNAT DP Testing')
        if options.pertenantnatepg:
            print('Test for PER_TENANT_NAT_EPG FOR DNAT')
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
        objs_uuid = gbpheat.get_uuid_from_stack(
                    dnat_heat_temp,
                    heat_stack_name
                    )
        objs_uuid['external_gw'] = extgw
        objs_uuid['ostack_controller'] = cntlr_ip
        objs_uuid['ipsofextgw'] = ips_of_extgw
        objs_uuid['network_node'] = network_node
        objs_uuid['pausetodebug'] = pausetodebug
        objs_uuid['routefordest'] = routefordest
        # Verify the config setup on the ACI
        print('Sleeping for the EP learning on ACI Fab')
        sleep(30)   
        """ #JISHNU: commented out for now 07/25/17
        if options.pertenantnatepg:
            if not testbed_cfg.verifySetup(nat_type,
                                           pertntnatEpg=True):
                testbed_cfg.cleanup()
                preExistcfg(cntlr_ip,revert=True)
                print \
                    'DNAT-PerTntNatEpg TestSuite Execution Failed'
                sys.exit(1)
        else:
            if not testbed_cfg.verifySetup(nat_type):
                testbed_cfg.cleanup()
                preExistcfg(cntlr_ip,revert=True)
                print \
                    'DNAT TestSuite Execution Failed'
                sys.exit(1)
        """
        # Note: Please always maintain the below order of DNAT Test Execution
        # Since the DNAT_VM_to_VM has the final blind cleanup, which helps to
        # avoid the heat stack-delete failure coming from nat_dp_main_config
        
        # Execution of DNAT DP Tests from ExtRtr to VMs
        from testcases.testcases_dp_nat.testsuite_dnat_extgw_to_vm \
        import DNAT_ExtGw_to_VMs
        test_dnat_extgw_to_vm = DNAT_ExtGw_to_VMs(objs_uuid,
                                                 targetVmFips)

        test_dnat_extgw_to_vm.test_runner(preexist)
        # If integ=True, then ONLY repeat run of ExtRtr-VM Tests
        # no need for VM-to-VM, will enable if needed later
        if options.integ:
           runinteg(options.integ)
           if not testbed_cfg.verifySetup(nat_type):
              testbed_cfg.cleanup()
              #Revert Back the L3Out Config
              preExistcfg(cntlr_ip,revert=True)
              print('DNAT-Integ TestSuite Execution Failed after Reload %s'\
                  %(options.integ))
              sys.exit(1)
           test_dnat_extgw_to_vm.test_runner(preexist)
           print("\nDNAT-Integ TestSuite executed Successfully\n")
        # Execution of DNAT DP Test from VM to ExtGW and VM-to-VM    
        from testcases.testcases_dp_nat.testsuite_dnat_vm_to_vm \
        import DNAT_VMs_to_VMs
        test_dnat_vm_to_allvms = DNAT_VMs_to_VMs(objs_uuid, targetVmFips)
        test_dnat_vm_to_allvms.test_runner(preexist)
        # Cleanup
        testbed_cfg.cleanup()
        print("\nDNAT TestSuite executed Successfully\n")
        
    if nat_type == 'snat':
        # RUN ONLY SNAT DP TESTs
        # TestSetup Configuration
        print('Setting up global config for SNAT DP Testing')
        testbed_cfg.setup('snat', do_config=0)
        # Fetch gbp objects via heat output
        objs_uuid = gbpheat.get_uuid_from_stack(
                    testbed_cfg.snat_heat_temp,
                    testbed_cfg.heat_stack_name
                    )
        objs_uuid['external_gw'] = testbed_cfg.extgw
        objs_uuid['ostack_controller'] = testbed_cfg.cntlr_ip
        objs_uuid['ipsofextgw'] = testbed_cfg.ips_of_extgw
        objs_uuid['network_node'] = testbed_cfg.network_node
        objs_uuid['pausetodebug'] = testbed_cfg.pausetodebug
        # Verify the config setup on the ACI
        print('Sleeping for the EP learning on ACI Fab')
        sleep(30)   
        if not testbed_cfg.verifySetup(nat_type):
            testbed_cfg.cleanup()
            preExistcfg(cntlr_ip,revert=True)
            print('SNAT TestSuite Execution Failed due to Setup Issue')
            sys.exit(1)
        # Execution of SNAT DP Tests
        from testcases.testcases_dp_nat.testsuite_snat_vm_to_extgw \
        import SNAT_VMs_to_ExtGw
        test_snat_allvms_to_extgw = SNAT_VMs_to_ExtGw(objs_uuid)
        test_snat_allvms_to_extgw.test_runner(preexist)
        if options.integ:
           #Only Run ExtRtr-VM Tests, no need for VM-to-VM, will enable
           #if needed later
           runinteg(options.integ)
           if testbed_cfg.verifySetup(nat_type):
              testbed_cfg.cleanup()
              preExistcfg(cntlr_ip,revert=True)
              print('SNAT-Integ TestSuite Execution Failed after Reload %s'\
                  %(options.integ))
              sys.exit(1)
           test_dnat_extgw_to_vm.test_runner(preexist)
        # Cleanup after the SNAT Testsuite is run
        testbed_cfg.cleanup()
        print("\nSNAT TestSuite executed Successfully\n")

if __name__ == "__main__":
    main()
