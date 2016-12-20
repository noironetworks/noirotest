#!/usr/bin/python

import logging
import pprint
import re
import string
import sys
from time import sleep
from libs.gbp_aci_libs import *
from libs.gbp_utils import *
from libs.neutron import *
from libs.gbp_compute import *
from libs.gbp_pexp_traff_libs import gbpExpTraff
from testcases.config import conf

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
CNTRLIP = conf['controller_ip']
APICIP = conf['apic_ip']
TNT_LIST_ML2 =  ['FOO','BOOL']
TNT_LIST_GBP = ['MANDRAKE','GARTH']
ML2vms = {'FOO' : ['FVM1','FVM2'], 'BOOL' : ['BVM3']}
GBPvms = {'MANDRAKE' : ['MVM1','MVM2'], 'GARTH' : ['GVM3']}
EXTRTR = conf['ext_gw_rtr']
EXTRTRIP1 = conf['fip1_of_extgw']
EXTRTRIP2 = conf['fip2_of_extgw']
AVZONE = conf['nova_az_name']
AVHOST = conf['az_comp_node']
COMPUTE1 = conf['ntk_node']
COMPUTE2 = conf['compute_2']
EXTDNATCIDR,FIPBYTES = '50.50.50.0/28', '50.50.50.'
EXTSNATCIDR = '55.55.55.0/28'
comp1 = Compute(COMPUTE1)
comp2 = Compute(COMPUTE2)
neutron = neutronCli(CNTRLIP)
neutron_api = neutronPy(CNTRLIP)
apic = gbpApic(APICIP)

class crudML2(object):
    global tnt1, tnt2, ml2Ntks, ml2Subs, tnt1sub, tnt2sub, Cidrs, vms
    tnt1, tnt2 = TNT_LIST_ML2[0],TNT_LIST_ML2[1]
    ml2Ntks,ml2Subs,Cidrs,vms = {},{},{},{}
    ml2Ntks[tnt1] = ['Net1', 'Net2']
    ml2Ntks[tnt2] = ['ntk3']
    ml2Subs[tnt1] = ['Subnet1', 'Subnet2']
    ml2Subs[tnt2] = ['sub3']
    Cidrs[tnt1] = ['1.1.1.0/28','2.2.2.0/28']
    Cidrs[tnt2] = ['3.3.3.0/28']
    vms[tnt1] = ML2vms[tnt1]
    vms[tnt2] = ML2vms[tnt2]
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
 			       cidr=EXTSNATCIDR,extsub=True,aim=aimsnat)
      	except Exception as e:
	    LOG.error("Shared External Network Failed: "+repr(e))
            return 0
            
    def create_pvt_network_subnets(self):
        LOG.info(
        "\n#######################################################\n"
        "## Create Private Network & Subnet for both ML2 Tenants ##\n"
        "#########################################################\n"
        )
	self.subnetIDs = {}
	self.networkIDs = {}
	self.netIDnames = {}
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
        print self.netIDnames
	print self.networkIDs
	print self.subnetIDs

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
	vm_ntk_ip = {}
        neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default icmp -1 -1 0.0.0.0/0'
            % (tnt))
        neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default tcp 22 22 0.0.0.0/0'
            % (tnt))
        az = neutron.alternate_az(AVZONE)
        for i in range(len(vms[tnt])):
            try:
		n = self.networkIDs[tnt][i]
                vmcreate = neutron.spawnVM(tnt,
                                           vms[tnt][i],
                                           self.networkIDs[tnt][i],
                                           availzone=az.next()
                                       	   )
		vm_ntk_ip[vms[tnt][i]] = [vmcreate[0],self.networkIDs[tnt][i]]
	    except Exception as e:
                LOG.error('VM Creation for tnt %s Failed: ' %(tnt)+repr(e))
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
    #Ensure to inherit/instantiate the class after 
    #all VMs are created
    def __init__(self,vm_ntk_ip):
  	self.traff_from_vm = {}
	pingable_ips = [ip for val in vm_ntk_ip.values() for ip in x][0::2]+\
			[EXTRTRIP1,EXTRTRIP2]
	for vm,prop in vm_ntk_ip.iteritems():
	    dest_ips = pingable_ips
	    self.traff_from_vm[vm] = {'netns' : 'qdhcp-'+prop[1],
				      'src_ip' : prop[0],
				      'dest_ip' : dest_ips.remove(prop[0])
				     }
	
    def traff_from_vm(self,vmname):
	vm_traff = gbpExpTraff(COMPUTE1,self.traff_from_vm['netns'],
				self.traff_from_vm['src_ip'],
				self.traff_from_vm['dest_ip'])
	
	return vm_traff.run_and_verify_traffic(proto,tcp_syn_only=1)


