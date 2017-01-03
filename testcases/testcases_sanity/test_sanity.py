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
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_pexp_traff_libs import gbpExpTraff
from testcases.config import conf

# Initialize logging
LOG = logging.getLogger(__name__)
LOG.propagate = False
LOG.setLevel(logging.ERROR)
# create a logfile handler
hdlr = logging.FileHandler('/tmp/test_ml2_sanity.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)
# Add the handler to the logger
LOG.addHandler(hdlr)

#Extract and set global vars from config file
#NOTE:The external-segment is hardcoded to 'Management-Out'
CNTRLIP = conf['controller_ip']
APICIP = conf['apic_ip']
TNT_LIST_ML2 =  ['FOO','BOOL']
TNT_LIST_GBP = ['MANDRAKE','GARTH']
ML2vms = {'FOO' : ['FVM1','FVM2'], 'BOOL' : ['BVM3', 'BVM4']}
GBPvms = {'MANDRAKE' : ['MVM1','MVM2','MVM3','MVM4'],
          'GARTH' : ['GVM3','GVM4']}
EXTRTR = conf['ext_gw_rtr']
EXTRTRIP1 = conf['fip1_of_extgw']
EXTRTRIP2 = conf['fip2_of_extgw']
AVZONE = conf['nova_az_name']
AVHOST = conf['az_comp_node']
COMPUTE1 = conf['ntk_node']
COMPUTE2 = conf['compute_2']
EXTDNATCIDR,FIPBYTES = '50.50.50.0/28', '50.50.50.'
EXTSNATCIDR = '55.55.55.0/28'
vm_ntk_ip = {}
comp1 = Compute(COMPUTE1)
comp2 = Compute(COMPUTE2)
neutron = neutronCli(CNTRLIP)
neutron_api = neutronPy(CNTRLIP)
apic = gbpApic(APICIP)

class crudML2(object):
    global ml2tnt1, ml2tnt2, ml2Ntks, ml2Subs, Cidrs, addscopename, \
	   subpoolname, subpool
    ml2tnt1, ml2tnt2 = TNT_LIST_ML2[0],TNT_LIST_ML2[1]
    ml2Ntks,ml2Subs,Cidrs = {},{},{}
    ml2Ntks[ml2tnt1] = ['Net1', 'Net2']
    ml2Ntks[ml2tnt2] = ['ntk3', 'ntk4']
    ml2Subs[ml2tnt1] = ['Subnet1', 'Subnet2']
    ml2Subs[ml2tnt2] = ['sub3', 'sub4']
    addscopename = 'asc1'
    subpoolname = 'subpool1'
    subpool = '22.22.22.0/24'
    Cidrs[ml2tnt1] = ['11.11.11.0/28', '21.21.21.0/28']
    print "Before Keystone Add is invoked tenant-list == ", TNT_LIST_ML2 
    print "Global ML2 vm list == ", ML2vms[ml2tnt1]
    print "Global ML2 vm list == ", ML2vms[ml2tnt2]
    print "Global ML2 Tnt networks & subnets == ", ml2Ntks, ml2Subs

    def create_ml2_tenants(self):
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
            neutron.subnetcrud('extsub1','create','Management-Out',
 			       cidr=EXTDNATCIDR,extsub=True)
            neutron.subnetcrud('extsub2','create','Management-Out',
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
        for tnt in [ml2tnt1,ml2tnt2]:
            try:
                # Every Network has just one Subnet, 1:1
                self.subnetIDs[tnt] = []
                self.networkIDs[tnt] = []
                self.netIDnames[tnt] = {}
                for index in range(len(ml2Ntks[tnt])):
                    network = ml2Ntks[tnt][index]
                    subnet = ml2Subs[tnt][index]
                    netID = neutron.netcrud(network,'create',tnt)
                    self.netIDnames[tnt][network] = netID
                    self.networkIDs[tnt].append(netID)
		    if tnt == ml2tnt1:
                        cidr = Cidrs[tnt][index]
                        self.subnetIDs[tnt].append(
                                        neutron.subnetcrud(subnet,
                                                           'create',
                                                           netID,
                                                           cidr=cidr,
                                                           tenant=tnt))
		    else:
			self.subnetIDs[tnt].append( 
                                        neutron.subnetcrud(subnet,
                                                           'create',
                                                           netID,
                                                           subnetpool=self.subpoolID,
                                                           tenant=tnt))
            except Exception as e:
               LOG.error('Create Network/Subnet Failed: '+repr(e))
	       return 0
        print self.netIDnames
	print self.networkIDs
	print self.subnetIDs

    def create_add_scope(self):
        LOG.info(
        "\n#############################################\n"
        "####  Create Address-Scope ONLY for Tenant %s ####\n"
        "###############################################\n"
        %(TNT_LIST_ML2[1]))
	self.addscopID = neutron.addscopecrud(addscopename,'create',
					      tenant=TNT_LIST_ML2[1])
	
    def create_subnetpool(self):
        LOG.info(
        "\n#############################################\n"
        "####  Create SubnetPool ONLY for Tenant %s ####\n"
        "###############################################\n"
        %(TNT_LIST_ML2[1]))
	self.subpoolID = neutron.subpoolcrud(subpoolname,'create',
                                             address_scope=addscopename,
					     pool=subpool,
					     tenant=TNT_LIST_ML2[1])
    
    def create_routers(self):
        LOG.info(
        "\n#############################################\n"
        "####  Create Router for both ML2 Tenants   ####\n"
        "###############################################\n"
        )
        self.rtrIDs = {}
        for tnt in [ml2tnt1,ml2tnt2]:
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
        neutron.runcmd(
            'nova --os-tenant-name %s secgroup-add-rule default tcp 80 80 0.0.0.0/0'
            % (tnt))
        az = neutron.alternate_az(AVZONE)
        for i in range(len(ML2vms[tnt])):
            try:
		n = self.networkIDs[tnt][i]
                vmcreate = neutron.spawnVM(tnt,
                                           ML2vms[tnt][i],
                                           self.networkIDs[tnt][i],
                                           availzone=az.next()
                                       	   )
		vm_ntk_ip[ML2vms[tnt][i]] = [vmcreate[0],self.networkIDs[tnt][i]]
	    except Exception as e:
                LOG.error('VM Creation for tnt %s Failed: ' %(tnt)+repr(e))
                return 0

    def attach_fip_to_vms(self,tnt):
        LOG.info(
        "\n#############################################\n"
        "#### Create & Attach FIP to VMs for the Tenant %s ####\n"
        "###############################################\n"
	%(tnt))
	for vm in ML2vms[tnt]:
	    cmd1 = 'nova --os-tenant-name %s' %(tnt)+\
                  ' floating-ip-create Management-Out'
	    match = re.search('(%s\d+).*'%(FIPBYTES),
                                        neutron.runcmd(cmd1),
					re.I)
	    if match:
		fip = match.group(1)
	    cmd2 = 'nova --os-tenant-name %s ' %(tnt)+\
                   'floating-ip-associate %s %s' %(vm,fip)
	    neutron.runcmd(cmd2)

	    
class crudGBP(object):
    #For now we will run with single tenant,
    #once 'shared' is supported, we will run
    #with two tenants sharing a single L3P
    from libs.gbp_nova_libs import gbpNova
    global tnt1, tnt2, vms, gbpL3p, gbpL2p, ippool
    tnt1, tnt2 = TNT_LIST_GBP
    gbpL3p = 'L3P1'
    gbpL2p = {tnt1 : ['L2P1','L2P2']}
    ippool = {tnt1 : '70.70.70.0/24',
              tnt2 : '80.80.80.0/24'}
    vms = {}
    vms[tnt1] = GBPvms[tnt1]
    vms[tnt2] = GBPvms[tnt2]

    def create_gbp_tenants(self):
        neutron.addDelkeystoneTnt(TNT_LIST_GBP, 'create')
        self.gbptnt1 = GBPCrud(CNTRLIP,tenant=tnt1)
        self.gbptnt2 = GBPCrud(CNTRLIP,tenant=tnt2)
        self.gbpadmin = GBPCrud(CNTRLIP)
        self.novatnt1 = gbpNova(CNTRLIP,tenant=tnt1)
        self.novatnt2 = gbpNova(CNTRLIP,tenant=tnt2)
    
    def create_l2p(self):
        LOG.info(
        "\n################################################################\n"
        "## Create Explicit L2Policies, Auto-PTGs & implicit L3Policy for Tenant %s ##\n"
        "##################################################################\n"
	%(tnt1))
	self.l2p1_uuid,self.l2p1_impl3p,self.l2p1_autoptg = \
             self.gbptnt1.create_gbp_l2policy(gbpL2p[tnt1][0],getl3p=True,autoptg=True)
        LOG.info(
        "\n## Create explcit L2Policy associated to above implicit L3Policy ##\n"
	)
	self.l2p2_uuid,self.l2p2_autoptg = self.gbptnt1.create_gbp_l2policy(gbpL2p[tnt1][1],
                                                         autoptg=True,
   				                         l3_policy_id=self.l2p1_impl3p)
	if not self.l2p2_uuid or not self.l2p2_autoptg\
	   or not self.l2p1_uuid or not self.l2p1_impl3p\
	   or not self.l2p1_autoptg:
	     return 0
	else:
	    LOG.info(
	    "\n## Following resources have been created for Tenant %s:\n"
	    "Implicitly-created L3Policy = %s\n"
	    "Explicit L2Policy_1 = %s and its AutoPTG = %s\n"
	    "Explicit L2Policy_2 = %s and its AutoPTG = %s\n"
	    %(tnt1, self.l2p1_impl3p, self.l2p1_uuid, self.l2p1_autoptg,
	    self.l2p2_uuid, self.l2p2_autoptg))
  	
    def create_ptg(self):
        LOG.info(
        "\n################################################\n"
        "## Create Explicit PTG using L2P1 for Tenant %s ##\n"
        "##################################################\n"
	%(tnt1))
	self.reg_ptg = self.gbptnt1.create_gbp_policy_target_group(
				'REGPTG',
				l2_policy_id=self.l2p1_uuid
				)
	if not self.reg_ptg:
		 return 0

    def create_policy_target(self):
        LOG.info(
        "\n################################################\n"
        "## Create Policy-Targets for two Auto-PTGs and one\n"
        "## Regular PTG for Tenant %s ##\n"
        "##################################################\n"
	%(tnt1))
	if self.reg_ptg and self.l2p1_autoptg and self.l2p2_autoptg:
	    #Two PTs will be created out of self.l2p2_autoptg, so repeating
	    #the element in the list, such that this list and ptlist length
	    #are same
	    self.ptgs = [self.l2p1_autoptg, self.l2p2_autoptg, self.l2p2_autoptg,\
		         self.reg_ptg]
	else:
	    LOG.error(
		    "Cannot create PTs since some PTGs are not yet initialized"
		     )
	    return 0
	self.vm_to_port = {}
        self.vms = GBPvms[tnt1]
	self.ptlist = ['pt1','pt2','pt3','pt4']
	for i in range(len(self.ptlist)):
	    pt = self.ptlist[i]
	    vm = self.vms[i]
	    ptg = self.ptgs[i]
	    self.vm_to_port[vm] = self.gbptnt1.create_gbp_policy_target(
       			          pt, ptg, ptg_property='uuid')[1]
	print self.vm_to_port
	if 0 in self.vm_to_port.values():
	    LOG.error("\nNot all PTs are created properly = %s"
                     %(self.vm_to_port))
	    return 0
	    
    def install_tenant_vms(self):
        LOG.info(
        "\n################################################\n"
        "## Create VMs for Tenant %s ##\n"
        "##################################################\n"
        %(tnt1))
        az = neutron.alternate_az(AVZONE)
        for vm,port in self.vm_to_port.iteritems():
            if not self.novatnt1.vm_create_api(vm,
                                      'ubuntu_multi_nics',
                                      port,
                                      avail_zone=az.next()) == 0:
                self._log.error("\n//// %s Create failed ////" %(vm))
                return 0

    def create_ext_seg(self):
        LOG.info(
        "\n########################################################\n"
        "## Create External Segment as shared under tenant-Admin ##\n"
        "##########################################################\n"
        )
        self.extsegid = gbpadmin.create_gbp_external_segment(
                                        Management-Out,
                                        external_routes = [{
                                           'destination':'0.0.0.0/0',
                                           'nexthop': None}],
				       	shared=True
                                       )
        if self.extsegid == 0:
            self._log.error(
            "\n///// Step: External Segment Creation %s failed /////"
            %(extsegname))
            return 0
	
class verifyML2(object):
      def __init__(self):
	return 1


class sendTraffic(object):
    #Ensure to inherit/instantiate the class after 
    #all VMs are created
    def generate_vm_prop(self,ext=False):
	print 'VM_to_NTK_IP inside Traffi Class == ', vm_ntk_ip
  	properties = {}
	if ext:
	    pingable_ips = [ip for val in vm_ntk_ip.values() for ip in val][0::2]+\
			[EXTRTRIP1,EXTRTRIP2]
	else:
	    pingable_ips = [ip for val in vm_ntk_ip.values() for ip in val][0::2]
	for vm,prop in vm_ntk_ip.iteritems():
	    if ext:
	        pingable_ips = [ip for val in vm_ntk_ip.values() for ip in val][0::2]+\
			[EXTRTRIP1,EXTRTRIP2]
	    else:
	        pingable_ips = [ip for val in vm_ntk_ip.values() for ip in val][0::2]
	    pingable_ips.remove(prop[0]) #Removing the Src_IP from the list of pingable_ips
	    dest_ips = pingable_ips
	    properties[vm] = {'netns' : 'qdhcp-'+prop[1],
				      'src_ip' : prop[0],
				      'dest_ip' : dest_ips
				     }
	return properties
	
    def traff_from_ml2_tenants(self,tnt,ext=False,proto=['icmp','tcp']):
	LOG.info(
        "\n#############################################\n"
        "## Sending Traffic from VMs in ML2-tenant %s ##\n"
        "###############################################\n"
        %(tnt))
	tenant_vms  = ML2vms[tnt]
	vm_property = self.generate_vm_prop(ext=ext)
	print "VM Properties == ", vm_property
	for vm in tenant_vms:
	    vm_traff = gbpExpTraff(COMPUTE1,vm_property[vm]['netns'],
				vm_property[vm]['src_ip'],
				vm_property[vm]['dest_ip'])
	    return vm_traff.run_and_verify_traffic(proto,tcp_syn_only=1)


