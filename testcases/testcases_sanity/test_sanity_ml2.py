#!/usr/bin/python

import logging
import pprint
import string
import sys
import yaml
from time import sleep
from libs.gbp_aci_libs import *
from libs.gbp_utils import *
from libs.neutron import *
from libs.gbp_compute import *


# Initialize logging
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
# create a logfile handler
hdlr = logging.FileHandler('/tmp/test_ml2_nat.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)
# Add the handler to the logger
LOG.addHandler(hdlr)

#Extract and set global vars from config file
cfgfile = sys.argv[1]
with open(cfgfile, 'rt') as f:
     conf = yaml.load(f)
CNTRLIP = conf['controller_ip']
APICIP = conf['apic_ip']
TNT_LIST_ML2 =  ['FOO','BOOL']
TNT_LIST_GBP = ['COKE','GRASS']
EXTRTR = conf['ext_rtr']
EXTRTRIP1 = conf['extrtr_ip1']
EXTRTRIP2 = conf['extrtr_ip2']
AVZONE = conf['nova_az_name']
AVHOST = conf['az_comp_node']
NOVAHOST = conf['az_nova_comp_node']
NETNODE = conf['network_node']
COMPUTE1 = conf['compute-1']
COMPUTE2 = conf['compute-2']
EXTDNATCIDR = '50.50.50.0/28'
EXTSNATCIDR = '55.55.55.0/28'

class crudML2(object):
        global comp1 comp2 tnt1 tnt2 ml2Ntks ml2Subs tnt1sub tnt2sub neutron\
               apic Cidrs
        comp1 = Compute(COMPUTE1)
        comp2 = Compute(COMPUTE2)
        neutron = neutronCli(CNTRLIP)
        apic = GbpApic(APICIP)
        tnt1, tnt2 = TNT_LIST_ML2[0],TNT_LIST_ML2[1]
        ml2Ntks,ml2Subs,Cidrs = {},{},{}
        ml2Ntks[tnt1] = ['Net1', 'Net2']
        ml2Ntks[tnt2] = ['ntk3']
        ml2Subs[tnt1] = ['Subnet1', 'Subnet2']
        ml2Subs[tnt2] = ['sub3']
        Cidrs[tnt1] = ['1.1.1.0/28','2.2.2.0/28']
        Cidrs[tnt2] = ['3.3.3.0/28']
        neutron.addDelkeystoneTnt(TNT_LIST_ML2, 'create')

    def create_external_network_subnets(self):
        LOG.info(
        "\n#######################################################\n"
        "####  Create Shared External Network for ML2 Tenants   ####\n"
        "#########################################################\n"
        )
        aimntkcfg = '--apic:distinguished_names type=dict'+\
                 ' ExternalNetwork='+\
                 'uni/tn-common/out-Management-Out/instP-MgmtExtPol'
        aimsnat = '--apic:snat_host_pool True'
	print aimntkcfg
	try:
	    neutron.netcrud('Management-Out','create',external=True,
                            shared=True, aim = aimntkcfg)
            neutron.subnetcrud('extsub1','create',ntkNameId='Management-Out',
 			       cidr=EXTDNATCIDR,extsub=True)
            neutron.subnetcrud('extsub2','create',ntkNameId='Management-Out',
 			       cidr=EXTDNATCIDR,extsub=True,aim=aimsnat)
      	except Exception as e:
	    LOG.error("Shared External Network Failed: "+repr(e))
            return 0
            
    def create_pvt_network_subnets(self):
        LOG.info(
        "\n#######################################################\n"
        "## Create Private Network & Subnet for both ML2 Tenants ##\n"
        "#########################################################\n"
        )
        for tnt in [tnt1,tnt2]:
            try:
                # Every Network has just one Subnet, 1:1
                self.subnetIDs[tnt] = []
                self.networkIDs[tnt] = []
                self.netIDnames[tnt] = {}
                for index in range(len(ml2Ntks[tnt])):
                    network = ml2Ntks[tnt][index]
                    subnet = ml2Subs[tnt][index]
                    cidr = Cidrs[tnt][index]
                    netID = neutron.netcrud(network,'create',tnt)
                    self.netIDnames[tnt][netID] = network
                    self.networkIDs[tnt].append(netID)
                    self.subnetIDs[tnt].append(
                                        neutron.subnetcrud(subnet,
                                                           'create',
                                                           ntkNameId=netID,
                                                           cidr=cidr,
                                                           tenant=tnt))
            except Exception as e:
               LOG.error('Create Network/Subnet Failed: '+repr(e))
	       return 0

    def create_routers(self):
        LOG.info(
        "\n#############################################\n"
        "####  Create Router for both ML2 Tenants   ####\n"
        "###############################################\n"
        )
        self.rtrIDs = {}
        for tnt in [tnt1,tnt2]:
            try:
                _id = neutron.rtrcrud('RTR1', 'create', tenant=tnt)
                self.rtrIDs[tnt] = _id
            except Exception as e:
       		LOG.error('Create Router Failed: '+repr(e))
                return 0
        LOG.info("\nRouter IDs for the respective Tenants == %s" %
                 (self.rtrIDs))

    def attach_routers_to_networks(self,tnt):
        LOG.info(
        "\n#############################################\n"
        "####  Attach Router to networks of the tenant %s ####\n"
        "###############################################\n"
         %(tnt))
        for subnetId in self.subnetIDs[tnt]:
            try:
                neutron.rtrcrud(self.rtrIDs[tnt],'add',rtrprop='interface',\
                            subnet=subnetId, tenant=tnt)
	    except Exception as e:
		LOG.error('Attach Router to Network Failed: '+repr(e))
		return 0
    
    def attach_router_to_extnw(self,tnt):
        LOG.info(
        "\n#############################################\n"
        "####  Attach %s Router to the External Network ####\n"
        "###############################################\n"
	%(tnt))
 	try:
	    neutron.rtrcrud(self.rtrIDs[tnt], 'set', rtrprop='gateway',
	   		    gw='Management-Out', tenant=tnt)
	except Exception as e:
	    LOG.error('Setting GW for the Router Failed: ' + repr(e))
	    return 0

    def install_tenant_vms(self,tnt):
        LOG.info(
        "\n#############################################\n"
        "####  Install VM for the Tenant %s  ####\n"
        "###############################################\n"
	%(tnt))
        # Since VMs are created with 'default' secgroup, hence
        # adding rules to the default secgroup
        neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default icmp -1 -1 0.0.0.0/0'
            % (tnt)
        )
        neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default tcp 22 22 0.0.0.0/0'
            % (tnt)
        )
        self.NETtoVM = {}
        vm_num = 1
        i = 0  # Intent is to place VMs alternately on two comp-nodes
        avzonetoHost = [self.avhost, self.novahost]
        for netid, name in self.netIDnames[self.tnt1].iteritems():
            self.NETtoVM[name] = {}
            self.vmname = '%s-VM-' % (self.tnt1) + str(vm_num)
            if i:
                avzone = 'nova'
                avhost = self.novahost
            else:
                avzone = self.avzone
                avhost = self.avhost
            vmcreate = neutron.spawnVM(self.tnt1,
                                            self.vmname,
                                            netid,
                                            availzone='%s' % (
                                                avzone)
                                            )
            # vmcreate: label for the return value which is
            # [vmip,portID,portMAC]
            i += 1
            if i > 1:
                i = 0
            if not vmcreate:
                LOG.error("\nStep-4-TC-5:Fail: VM Creation Failed")
                return 0
            else:
                self.NETtoVM[name][self.vmname] = vmcreate
            vm_num = vm_num + 1

        LOG.info("\n# Step-5-TC-5:VerifyACI: Verify the Endpoint Learnings #")
        LOG.info("\nSleeping for 30 secs for the Opflex-Agent to send GARP")
        sleep(30)
        getEp = self.apic.getEpgOper(self.tnt1)
        if getEp:
            for net in self.netNames[self.tnt1]:
                vm = self.NETtoVM[net].keys()[0]
                print 'JISHNU VM == ',vm
                print 'JISHNU CHECK in KEYs = ',getEp[net].keys()
                print 'JISHNU Status in VM = ',getEp[net][vm]['status']
                if not vm in getEp[net].keys() \
                   or getEp[net][vm]['status'] != 'learned,vmm':
                    LOG.error(
                        "\nStep-5-TC-5:Fail: EP Learning failed on APIC")
                    return 0

        LOG.info(
            "\n# Step-6-TC-5: Verify: EP files of VMs refers domain-name to Routers' VRF #")
        for key, val in self.NETtoVM.iteritems():  # key=Network name
            for value in val.itervalues():
                vmip, vmportID, vmportMAC = value
                if not self.comp2.verify_EpFile(
                    vmportID,
                    vmportMAC,
                    endpoint_group_name='%s|%s' % (self.apicsystemID, key),
                    domain_name='_%s_%s' % (self.apicsystemID, self.rtrID)
                ) and \
                    not self.comp1.verify_EpFile(
                        vmportID,
                        vmportMAC,
                        endpoint_group_name='%s|%s' % (self.apicsystemID, key),
                        domain_name='_%s_%s' % (self.apicsystemID, self.rtrID)
                ):
                    LOG.error(
                        "\nStep-6-TC-5:Fail: Incorrect values/attributes in EP file")
                    return 0

        LOG.info(
            "\n Step-7-TC-5: Verify: rdConfig of the tenant refers to Routers's VRF #")
        if not self.comp2.verify_rdConfig(self.tnt1,
                                          self.rtrID,
                                          self.subNames[self.tnt1]
                                          ) and \
            not self.comp1.verify_rdConfig(self.tnt1,
                                           self.rtrID,
                                           self.subNames[self.tnt1]
                                           ):
            LOG.error(
                "\nStep-7-TC-5:Fail: Incorrect values/attributes in rdConfig file")
            return 0

        LOG.info(
            "\n Step-8-TC-5: Verify Traffic between the VMs across networks in the tenant #")

    def test_vpr_snat_func_6(self):
        """
        Testcase-6 in VPR-SNAT-Functionality Workflow
        """
        LOG.info(
       "\n##############  Testcase TEST_VPR_NAT_FUNC_6 ###############\n"
       "# Attach TC-5's Router in a given tenant to the ExtNetwork   #\n"
       "# Attach router to multiple networks in a given tenant       #\n"
       "# Verify: EP Files has SNAT mapping set correctly	       #\n"
       "# VerifyACI: ShadowL3Out's VRF resolves to Routers' VRF      #\n"
       "# VerifyACI: SNAT EPs are learned in the NAT-EPGs	       #\n"
       "# Verify: Traffic between the VMs across networks in the tenant #\n"
       "# Verify: Traffic between the VMs and External Router	       #\n"
       "##############################################################\n"
        )
        LOG.info("\n Execution of Testcase starts #")

        LOG.info(
            "\nStep-1-TC-6: Attach TC-5's Router in a given tenant to the ExtNetwork   #")
        neutron.rtrcrud(self.rtrID, 'set', rtrprop='gateway',
                             gw='Management-Out', tenant=self.tnt1)
        LOG.info(
            "\nStep-2-TC-6: Attach router to multiple networks in a given tenant #")
        # The router is already attached to multiple nets of the tenant in TC-5
	sleep(20) #Just to let the change percolate to ACI 
        LOG.info("\nStep-3-TC-6: Verify: SNAT EP exists in the computes #")
        netnodeSnat = self.comp1.getSNATEp('Management-Out')
        comp2Snat = self.comp2.getSNATEp('Management-Out')
        if netnodeSnat:
            nn_snatintf, self.nn_snatip, nn_snattnt, self.nn_snatepg, self.nn_snatep = netnodeSnat
        else:
            LOG.info("\nStep-3-TC-6:Fail: SNAT EP not found in Network-Node")
            return 0
        if comp2Snat:
            cn_snatintf, self.cn_snatip, cn_snattnt, cn_snatepg, cn_snatep = comp2Snat
        else:
            LOG.info("\nStep-3-TC-6:Fail: SNAT EP not found in Compute-Node")
            return 0

        LOG.info(
            "\nStep-4-TC-6: VerifyACI: ShadowL3Out's VRF resolves to Routers' VRF #")
        ShdL3 = self.apic.getL3Out(self.tnt1)
        if len(ShdL3):
            if '_Shd-%s-' % (self.rtrID) in ShdL3.keys()[0]:
                if ShdL3.values()[0]['vrfname'] == '_%s_%s' % (self.apicsystemID, self.rtrID) \
                        and ShdL3.values()[0]['vrfstate'] == 'formed':
                    print "Vrf name and state matched"
                else:
                    LOG.info(
                    "\nStep-4-TC-6: Fail: VRfname or VRfState one or both did not match")
                    return 0
            else:
                LOG.info("\nStep-4-TC-6: Fail: Shadow L3Out VRF not Found")
                return 0
        else:
            LOG.info("\nStep-4-TC-6: Fail: L3Outs not found in this tenant")
            return 0
        #TBD:JISHNU >>below check is incorrect, Moreover keep a check for ip-mapping,
        #vrf_per_router_tenant MUST be added /deleted as part of this suite. The suite
        #should run seamlessly with and without the config_flag
        #TBD: JISHNU .. also add the router to all subnets for neutron behavior
        LOG.info("\nStep-6-TC-6:VerifyACI: SNAT EPs are learned in the NAT-EPGs #")
        if not self.verifySnatEpsOnAPIC(self.novahost,
                               self.nn_snatepg,
                               self.nn_snatip):
            LOG.error(
                "\nStep-6-TC-6:Fail: Network-Node's SNATEP"\
                "%s Learning failed on APIC"\
                % (self.nn_snatip))
        if not self.verifySnatEpsOnAPIC(self.avhost,
                               self.nn_snatepg,
                               self.cn_snatip):
            LOG.error(
                "\nStep-6-TC-6:Fail: Compute-Node-2's SNATEP"\
                "%s Learning failed on APIC"\
                % (self.cn_snatip))

        LOG.info("\nStep-7-TC-6:Verify: Traffic between the VMs across networks in the tenant #")

        LOG.info("\nStep-8-TC-6: Verify: Traffic between the VMs and External Router #")

    def test_vpr_snat_func_7(self):
        """
        Testcase-7 in VPR-SNAT-Functionality Workflow
        """
        LOG.info(
        "\n##############  Testcase TEST_VPR_NAT_FUNC_7 ###############\n"
        "# Clear TC-5's Router GW in a given tenant to the ExtNetwork #\n"
        "# Attach TC-5's Tenant's Router to ExtNetwork GW             #\n"
        "# VerifyACI: ShadowL3Out's VRF resolves to Routers' VRF      #\n"
        "# VerifyACI: SNAT EPs are learned in the NAT-EPGs	       #\n"
        "# Verify: Traffic between the VMs and External Router	       #\n"
        "##############################################################\n"
        )
        LOG.info("\n Execution of Testcase starts #")

        LOG.info(
            "\nStep-1-TC-7: Clear TC-5's Router GW in a given tenant to the ExtNetwork #")
        neutron.rtrcrud(self.rtrID, 'clear', rtrprop='gateway',
                             tenant=self.tnt1)
        LOG.info(
            "\nStep-2-TC-7: Attach TC-5's Tenant's Router to ExtNetwork GW #")
        neutron.rtrcrud(self.rtrID, 'set', rtrprop='gateway',
                             gw='Management-Out', tenant=self.tnt1)
        sleep(10) #Just to let the change percolate to ACI
        LOG.info(
            "\nStep-3-TC-7: VerifyACI: ShadowL3Out's VRF resolves to Routers' VRF #")
        ShdL3 = self.apic.getL3Out(self.tnt1)
        if len(ShdL3):
            if '_Shd-%s-' % (self.rtrID) in ShdL3.keys()[0]:
                if ShdL3.values()[0]['vrfname'] == '_%s_%s' % (self.apicsystemID, self.rtrID) \
                        and ShdL3.values()[0]['vrfstate'] == 'formed':
                    print "Vrf name and state matched"
                else:
                    LOG.info(
                    "\nStep-3-TC-7: Fail: VRfname or VRfState one or both did not match")
                    return 0
            else:
                LOG.info("\nStep-3-TC-7: Fail: Shadow L3Out VRF not Found")
                return 0
        else:
            LOG.info("\nStep-3-TC-7: Fail: L3Outs not found in this tenant")
            return 0

        LOG.info("\nStep-4-TC-7:VerifyACI: SNAT EPs are learned in the NAT-EPGs #")
        if not self.verifySnatEpsOnAPIC(self.novahost,
                               self.nn_snatepg,
                               self.nn_snatip):
            LOG.error(
                "\nStep-4-TC-7:Fail: Network-Node's SNATEP"\
                "%s Learning failed on APIC"\
                % (self.nn_snatip))
        if not self.verifySnatEpsOnAPIC(self.avhost,
                               self.nn_snatepg,
                               self.cn_snatip):
            LOG.error(
                "\nStep-4-TC-7:Fail: Compute-Node-2's SNATEP"\
                "%s Learning failed on APIC"\
                % (self.cn_snatip))

        LOG.info("\nStep-5-TC-7: Verify: Traffic between the VMs and External Router #")

    def test_vpr_snat_func_8(self):
        """
        Testcase-8 in VPR-SNAT-Functionality Workflow
        """
        LOG.info(
        "\n########  Testcase TEST_VPR_NAT_FUNC_8 #####################\n"
        "# Clear TC-5's Router GW in a given tenant to the ExtNetwork #\n"
        "# Remove TC-5's Router from all attached private networks    #\n"
        "# Attach TC-5's Tenant's Router to ExtNetwork GW             #\n"
        "# Attach TC-5's Tenants Router to the private networks	      #\n"
        "# VerifyACI: VRF for attached BDs resolves to Routers' VRF   #\n"
        "# VerifyACI: ShadowL3Out's VRF resolves to Routers' VRF      #\n"
        "# VerifyACI: SNAT EPs are learned in the NAT-EPGs            #\n"
        "# Verify: Traffic between the VMs and External Router        #\n"
        "##############################################################\n")
        LOG.info("\n Execution of Testcase starts #")

        LOG.info(
        "\nStep-1-TC-8: Clear TC-6's Router GW in a given tenant to the ExtNetwork #")
        neutron.rtrcrud(self.rtrID, 'clear', rtrprop='gateway', tenant=self.tnt1)

        LOG.info(
        "\nStep-2-TC-8: Remove TC-5's Router from all attached private networks #"
        )
        for subnetId in self.subnetIDs[self.tnt1]:
            neutron.rtrcrud(self.rtrID, 'add', rtrprop='interface',
                                 subnet=subnetId, tenant=self.tnt1)
        for subnetId in self.new_subnetIDs[self.tnt1]:
            neutron.rtrcrud(self.rtrID, 'add', rtrprop='interface',
                                 subnet=subnetId, tenant=self.tnt1)
        LOG.info(
        "\nStep-3-TC-8: Attach TC-6's Tenant's Router to ExtNetwork GW #")
        neutron.rtrcrud(self.rtrID,
                            'set',
                            rtrprop='gateway',
                            gw='Management-Out',
                            tenant=self.tnt1)

        LOG.info(
        "\n# Step-4-TC-8: Attach router to multiple networks in a given tenant #")
        for subnetId in self.subnetIDs[self.tnt1]:
            neutron.rtrcrud(self.rtrID, 'add', rtrprop='interface',
                                 subnet=subnetId, tenant=self.tnt1)
        for subnetId in self.new_subnetIDs[self.tnt1]:
            neutron.rtrcrud(self.rtrID, 'add', rtrprop='interface',
                                 subnet=subnetId, tenant=self.tnt1)
        sleep(10) #Just to let the change percolate to ACI
        LOG.info(
        "\nStep-5-TC-8: VerifyACI: VRF for attached BDs resolves to Routers' VRF #"
        )
        unmatchedvrfs = self.verifyAciBDtoVRF({self.tnt1: self.rtrID})
        if unmatchedvrfs:
            LOG.error("\nStep-5-TC-8:Fail: Unresolved VRF for following BDs >> %s"
                      % (unmatchedvrfs))
            return 0
        
        LOG.info(
        "\nStep-6-TC-8: VerifyACI: ShadowL3Out's VRF resolves to Routers' VRF #"
        )
        ShdL3 = self.apic.getL3Out(self.tnt1)
        if len(ShdL3):
            if '_Shd-%s-' % (self.rtrID) in ShdL3.keys()[0]:
                if ShdL3.values()[0]['vrfname'] == '_%s_%s' % (self.apicsystemID, self.rtrID) \
                        and ShdL3.values()[0]['vrfstate'] == 'formed':
                    print "Vrf name and state matched"
                else:
                    LOG.info(
                    "\nStep-6-TC-8: Fail: VRfname or VRfState one or both did not match"
                    )
                    return 0
            else:
                LOG.info("\nStep-6-TC-8: Fail: Shadow L3Out VRF not Found")
                return 0
        else:
            LOG.info("\nStep-6-TC-8: Fail: L3Outs not found in this tenant")
            return 0

        LOG.info(
        "\nStep-7-TC-8:VerifyACI: SNAT EPs are learned in the NAT-EPGs #"
        )
        if not self.verifySnatEpsOnAPIC(self.novahost,
                               self.nn_snatepg,
                               self.nn_snatip):
            LOG.error(
                "\nStep-7-TC-8:Fail: Network-Node's SNATEP"\
                "%s Learning failed on APIC"\
                % (self.nn_snatip))
        if not self.verifySnatEpsOnAPIC(self.avhost,
                               self.nn_snatepg,
                               self.cn_snatip):
            LOG.error(
                "\nStep-7-TC-8:Fail: Compute-Node-2's SNATEP"\
                "%s Learning failed on APIC"\
                % (self.cn_snatip))
            return 0

        LOG.info("\nStep-8-TC-8: Verify: Traffic between the VMs and External Router #")

if __name__ == "__main__":
    main()
