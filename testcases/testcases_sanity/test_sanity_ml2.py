#!/usr/bin/python

import logging
import pprint
import re
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
EXTDNATCIDR,FIPBYTES = '50.50.50.0/28', '50.50.50.'
EXTSNATCIDR = '55.55.55.0/28'

class crudML2(object):
    global comp1 comp2 tnt1 tnt2 ml2Ntks ml2Subs tnt1sub tnt2sub neutron\
           apic Cidrs vms
    comp1 = Compute(COMPUTE1)
    comp2 = Compute(COMPUTE2)
    neutron = neutronCli(CNTRLIP)
    apic = GbpApic(APICIP)
    tnt1, tnt2 = TNT_LIST_ML2[0],TNT_LIST_ML2[1]
    ml2Ntks,ml2Subs,Cidrs,vms = {},{},{},{}
    ml2Ntks[tnt1] = ['Net1', 'Net2']
    ml2Ntks[tnt2] = ['ntk3']
    ml2Subs[tnt1] = ['Subnet1', 'Subnet2']
    ml2Subs[tnt2] = ['sub3']
    Cidrs[tnt1] = ['1.1.1.0/28','2.2.2.0/28']
    Cidrs[tnt2] = ['3.3.3.0/28']
    vms[tnt1] = ['FVM1','FVM2']
    vms[tnt2] = ['BVM3']
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
            % (tnt))
        neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default tcp 22 22 0.0.0.0/0'
            % (tnt))
        az = neutron.alternate_az(AVZONE)
        for i in range(len(vms[tnt])):
            try:
                vmcreate = neutron.spawnVM(tnt,
                                           vms[tnt][i],
                                           self.networkIDs[tnt][i],
                                           availzone=az.next()
                                       	   )
	    except Exception as e:
                LOG.error('VM Creation for tnt %s Failed' %(tnt))
                return 0

    def attach_fip_to_vms(self,tnt):
        LOG.info(
        "\n#############################################\n"
        "#### Create & Attach FIP to VMs for the Tenant %s ####\n"
        "###############################################\n"
	%(tnt))
	for vm in vms[tnt]:
	    cmd1 = 'nova --os-tenant-name %s' %(tnt)+\
                  ' floating-ip-create Management-Out'
	    fip = re.search('(%s\d+).*'%(FIPBYTES),
                                        run_openstack_cli(cmd1),
					re.I)
	    cmd2 = 'nova --os-tenant-name %s' %(tnt)+\
                   'floating-ip-associate %s %s' %(vm,fip)
	    run_openstack_cli(cmd2)

	    
class verifyML2(object):
      def __init__(self):
	return 1


class sendTraffic(object):
	# Access the VMs from netns
	# Send ICMP, TCP traffic(ExtGw, Fabric GW, VM-to-VM
	# VErify the results
