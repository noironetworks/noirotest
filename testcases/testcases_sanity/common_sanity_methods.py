#!/usr/bin/python

import logging
import re
import string
import subprocess
import sys
import uuid
from commands import *
getoutput("rm -rf /tmp/test_*") #Deletes pre-existing test logs
from time import sleep
from libs.gbp_aci_libs import *
from libs.gbp_utils import *
from libs.neutron import *
from libs.gbp_compute import *
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_pexp_traff_libs import gbpExpTraff
from testcases.config import conf
from testcases.testcases_nat_func.traff_from_extgw import *

SAUTO_L3OUT1 = 'sauto_l3out-1'
SAUTO_L3OUT2 = 'sauto_l3out-2'
L3OUT1=conf.get('primary_L3out')
L3OUT1_NET=conf.get('primary_L3out_net')
L3OUT2=conf.get('secondary_L3out')
L3OUT2_NET=conf.get('secondary_L3out_net')
L3OUT2_VRF=conf.get('secondary_L3out_vrf')
KEY_AUTH_IP = conf.get('keystone_ip')
RCFILE = conf.get('rcfile', 'overcloudrc')

max_traff_attempts = conf.get('traffic_attempts', 5)

# Initialize logging
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
# create a logfile handler
hdlr = logging.FileHandler('/tmp/test_sanity.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)
# Add the handler to the logger
LOG.addHandler(hdlr)

#Extract and set global vars from config file
#NOTE:The external-segment is hardcoded to L3OUT1
CNTRLIP = conf['controller_ip']
RESTIP = conf['rest_ip']
if isinstance(CNTRLIP, list):
    CNTRLIP = CNTRLIP[0]
APICIP = conf['apic_ip']
TNT_LIST_ML2 =  ['PENGUIN','OCTON','GARTH']
TNT_LIST_GBP = ['MANDRAKE', 'BATMAN']
ML2vms = {'PENGUIN' : ['PVM1','PVM2'],
	  'OCTON' : ['OVM3', 'OVM4'],
	  'GARTH' : ['GVM5', 'GVM6']}
GBPvms = {'MANDRAKE' : ['MVM1','MVM2','MVM3','MVM4'],
          'BATMAN' : ['BVM3','BVM4']}
EXTRTR = conf['ext_rtr']
EXTRTRIP1 = conf['extrtr_ip1']
EXTRTRIP2 = conf['extrtr_ip2']
AVZONE = conf['nova_az_name']
AVHOST = conf['az_comp_node']
COMPUTE1 = conf['network_node']
COMPUTE2 = conf['compute-2']
CTRLR_USER = conf['controller_user']
CTRLR_PSWD = conf['controller_password']
pausetodebug = conf['pausetodebug']
EXTDNATCIDR,FIPBYTES = '50.50.50.0/28', '50.50.50.'
EXTSNATCIDR = '55.55.55.0/28'
EXTNONATCIDR = '2.3.4.0/24' #Can be any cidr, jsut needed for neutron router
#We want to re-purpose the CIDR of PvtNtk for VMs participating in NO-NAT
NONATCIDR = '60.60.60.0/24'
NONATCIDRV6 = '2001:db8::/56'
APICVRF = "uni/tn-common/ctx-%s" % L3OUT2_VRF
ML2Fips = {}
GBPFips = {}
ACT = 'ALLOW'
CLS_ICMP = 'ICMP'
CLS_ICMPV6 = 'ICMPV6'
CLS_TCP = 'TCP'
PR_ICMP = 'PR-ICMP'
PR_ICMPV6 = 'PR-ICMPV6'
PR_TCP = 'PR-TCP'
PRS_ICMP_TCP = 'CONT-ICMP-TCP'
PRS_ICMP = 'CONT-ICMP'
PRS_TCP = 'CONT-TCP'
ml2_vm_ntk_ip = {}
gbp_vm_ntk_ip = {}
comp1 = Compute(COMPUTE1)
comp2 = Compute(COMPUTE2)
neutron = neutronCli(CNTRLIP, username=CTRLR_USER, password=CTRLR_PSWD)
neutron_api = neutronPy(CNTRLIP)


def is_dual_stack():
    return conf.get('dual_stack') and conf['dual_stack'] == 'True'


def create_external_network_subnets(nat):
	#Needed for both GBP & ML2
        LOG.info(
        "\n#######################################################\n"
        "####  Create Shared External Network for ML2 Tenants   ####\n"
        "#########################################################\n"
        )
	#For nonat, use pre-existing L3OUT2
	#Also just add one subnet to that nonat External-Network
	if nat == 'nonat':
            apic_dn = 'uni/tn-common/out-%(l3out)s/instP-%(l3out_net)s' % {
                'l3out': L3OUT2, 'l3out_net': L3OUT2_NET}
            aimntkcfg = '--apic:distinguished_names type=dict'+\
                 ' ExternalNetwork='+apic_dn+\
		 " --apic:nat_type ''"
	else:
            apic_dn = 'uni/tn-common/out-%(l3out)s/instP-%(l3out_net)s' % {
                'l3out': L3OUT1, 'l3out_net': L3OUT1_NET}
            aimntkcfg = '--apic:distinguished_names type=dict'+\
                 ' ExternalNetwork='+apic_dn
            aimsnat = '--apic:snat_host_pool True'
	try:
	    if nat == 'nonat':
	        neutron.netcrud(SAUTO_L3OUT2,'create',external=True,
                            shared=True, aim = aimntkcfg)
                EXTSUB3 = neutron.subnetcrud('extsub3','create',SAUTO_L3OUT2,
 			       cidr=EXTNONATCIDR,extsub=True)
		return EXTSUB3
	    else:
	        neutron.netcrud(SAUTO_L3OUT1,'create',external=True,
                            shared=True, aim = aimntkcfg)
                EXTSUB1 = neutron.subnetcrud('extsub1','create',SAUTO_L3OUT1,
 			       cidr=EXTDNATCIDR,extsub=True)
                EXTSUB2 = neutron.subnetcrud('extsub2','create',SAUTO_L3OUT1,
 			       cidr=EXTSNATCIDR,extsub=True,aim=aimsnat)
	        return EXTSUB1, EXTSUB2
      	except Exception as e:
	    LOG.error("Shared External Network Failed: "+repr(e))
            return 0

def attach_fip_to_vms(tnt,mode):
        LOG.info(
        "\n#############################################\n"
        "#### Create & Attach FIP to VMs for the Tenant %s ####\n"
        "###############################################\n"
	%(tnt))
	if mode == 'ml2':
	   vms = ML2vms[tnt]
	   ML2Fips[tnt]= []
	else:
	   vms = GBPvms[tnt]
	   GBPFips[tnt]=[]
	for vm in vms:
	    cmd1 = ('source ~/%s && neutron --os-project-name %s' %(RCFILE,tnt)+
                    ' floatingip-create %s -c id -f value' %(SAUTO_L3OUT1))
            fip_id = subprocess.check_output(['bash','-c', cmd1])
            fip_id = fip_id.split()[0]
	    cmd1 = ('source ~/%s && neutron --os-project-name %s' %(RCFILE,tnt)+
                    ' floatingip-show %s -c floating_ip_address -f value' %(fip_id))
            fip_data = subprocess.check_output(['bash','-c', cmd1])
	    match = re.search('(%s\d+).*'%(FIPBYTES),
                                        fip_data,
					re.I)
	    if match:
		fip = match.group(1)
	    	if mode == 'ml2':
		    ML2Fips[tnt].append(fip)
		else:
		    GBPFips[tnt].append(fip)
            # Get the fixed IP
            cmd1 = "source ~/%s && nova --os-project-name %s" % (RCFILE,tnt)
            cmd2 = " interface-list %s | grep ACTIVE | awk -F'|' '{print $3}'" % vm
            cmd = cmd1 + cmd2
            fixed_port_id = subprocess.check_output(['bash','-c', cmd])
            fixed_port_id = fixed_port_id.split()[0]
	    cmd2 = ('source ~/%s && neutron --os-project-name %s ' %(RCFILE,tnt)+
                    'floatingip-associate %s %s' %(fip_id,fixed_port_id))
            fip_data = subprocess.check_output(['bash','-c', cmd2])

def migrate_vm(mode,dest_host):
    from libs.gbp_nova import gbpNova
    if mode == 'ml2':
        nova = gbpNova(RESTIP,tenant=TNT_LIST_ML2[0])
        nova.vm_migrate(method='api')

def dump_results(mode):
    import commands
    text = commands.getoutput("grep -r %s-SANITY /tmp/test_sanity.log" %(mode)) 
    LOG.info("####### %s TEST RESULTS #######\n%s" %(mode,text))

class TestError(Exception):
	pass

class crudML2(object):
    global ml2tnt1, ml2tnt2, ml2tnt3, ml2Ntks, ml2Subs, Cidrs, addscopename, \
	   addscopename_shd, subpoolname, subpoolname_shd, subpool, \
           subpool_shd, traffic_class, addscopename_v6, addscopename_shd_v6, \
           subpoolname_v6, subpoolname_shd_v6, subpool_v6, subpool_shd_v6, CidrsV6, ml2SubsV6
    ml2tnt1, ml2tnt2, ml2tnt3 = TNT_LIST_ML2[0],TNT_LIST_ML2[1],TNT_LIST_ML2[2]
    ml2Ntks,ml2Subs,ml2SubsV6,Cidrs,CidrsV6 = {},{},{},{},{}
    ml2Ntks[ml2tnt1] = ['Net1', 'Net2']
    ml2Ntks[ml2tnt2] = ['ntk3', 'ntk4']
    ml2Ntks[ml2tnt3] = ['gntk5', 'gntk6']
    ml2Subs[ml2tnt1] = ['Subnet1', 'Subnet2']
    ml2Subs[ml2tnt2] = ['sub3', 'sub4']
    ml2Subs[ml2tnt3] = ['gsub5', 'gsub6']
    ml2SubsV6[ml2tnt1] = ['Subnet1V6', 'Subnet2V6']
    ml2SubsV6[ml2tnt2] = ['sub3V6', 'sub4V6']
    ml2SubsV6[ml2tnt3] = ['gsub5V6', 'gsub6V6']
    addscopename = 'asc1'
    addscopename_v6 = 'asc1v6'
    addscopename_shd = 'ascs'
    addscopename_shd_v6 = 'ascsv6'
    subpoolname = 'subpool1'
    subpoolname_v6 = 'subpool1v6'
    subpoolname_shd = 'sps'
    subpoolname_shd_v6 = 'spsv6'
    subpool = '22.22.22.0/24'
    subpool_v6 = '2001:db8:3::/56'
    subpool_shd = NONATCIDR #Repurposing subpool_shd for NONAT
    subpool_shd_v6 = NONATCIDRV6 #Repurposing subpool_shd for NONAT
    Cidrs[ml2tnt1] = ['11.11.11.0/28', '21.21.21.0/28']
    CidrsV6[ml2tnt1] = ['2001:db8:1::/64', '2001:db8:2::/64']

    def create_ml2_tenants(self):
	self.ml2tntIDs = neutron.addDelkeystoneTnt(TNT_LIST_ML2, 'create',getid=True)
	return None
    def create_pvt_network_subnets(self,nonat=False):
        LOG.info(
        "\n#######################################################\n"
        "## Create Private Network & Subnet for both ML2 Tenants ##\n"
        "#########################################################\n"
        )
	if nonat:
	    tntlist = [ml2tnt3]
	else:
	    tntlist = [ml2tnt1,ml2tnt2]
	self.subnetIDs = {}
	self.networkIDs = {}
	self.netIDnames = {}
        for tnt in tntlist:
            try:
                # Every Network has just one Subnet, 1:1
                self.subnetIDs[tnt] = []
                self.networkIDs[tnt] = []
                self.netIDnames[tnt] = {}
                for index in range(len(ml2Ntks[tnt])):
                        network = ml2Ntks[tnt][index]
                        subnet = ml2Subs[tnt][index]
                        subnet_v6 = ml2SubsV6[tnt][index]
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
                            if is_dual_stack():
                                cidr = CidrsV6[tnt][index]
                                self.subnetIDs[tnt].append(
                                            neutron.subnetcrud(subnet_v6,
                                                               'create',
                                                               netID,
                                                               cidr=cidr,
                                                               tenant=tnt))
		        elif tnt == ml2tnt3:
			    self.subnetIDs[tnt].append( 
                                        neutron.subnetcrud(subnet,
                                                           'create',
                                                           netID,
                                                           subnetpool=self.subpoolID,
                                                           tenant=tnt))
                            if is_dual_stack():
                               self.subnetIDs[tnt].append(
                                            neutron.subnetcrud(subnet_v6,
                                                               'create',
                                                               netID,
                                                               subnetpool=self.subpoolIDv6,
                                                               tenant=tnt))
		        else:
			    self.subnetIDs[tnt].append( 
                                        neutron.subnetcrud(subnet,
                                                           'create',
                                                           netID,
                                                           subnetpool=self.subpoolID,
                                                           tenant=tnt))
                            if is_dual_stack():
                               self.subnetIDs[tnt].append(
                                            neutron.subnetcrud(subnet_v6,
                                                               'create',
                                                               netID,
                                                               subnetpool=self.subpoolIDv6,
                                                               tenant=tnt))
            except Exception as e:
                   LOG.error('Create Network/Subnet Failed: '+repr(e))
	           return 0
        return self.netIDnames, self.networkIDs , self.subnetIDs

    def create_add_scope(self,tnt,shared=False,vrf=False):
        LOG.info(
        "\n#############################################\n"
        "####  Create Address-Scope ONLY for Tenant %s ####\n"
        "###############################################\n"
        %(tnt))
	if vrf: #Shared addresscope with attach VRF
	    self.addscopID = neutron.addscopecrud(addscopename_shd,
						'create',
					         tenant=tnt,
					         shared=shared,
						 apicvrf=APICVRF)
            if is_dual_stack():
               self.addscopIDv6 = neutron.addscopecrud(addscopename_shd_v6,
                                                        'create',
                                                        ip=6,
                                                        tenant=tnt,
                                                        shared=shared,
                                                        apicvrf=APICVRF)
  	else:
	    self.addscopID = neutron.addscopecrud(addscopename,
						'create',
					        tenant=tnt,
					        shared=shared)
            if is_dual_stack():
                vrfargs = ' -c apic:distinguished_names -f value'
                v4scope = neutron.addscopecrud(addscopename,
                                               'get',
                                               tenant=tnt,
                                               shared=shared,
                                               otherargs=vrfargs)
                regex = r'"VRF": "(.*)"'.encode('utf-8')
                found = re.search(regex, v4scope)
                if not found:
                    # It looks like different client versions use different
                    # formatting of the output
                    regex = r"'VRF': u'(.*)'"
                    found = re.search(regex, v4scope)
                    if not found:
                        regex = r"'VRF': '(.*)'"
                        found = re.search(regex, v4scope)
                self.addscopIDv6 = neutron.addscopecrud(addscopename_v6,
                                                        'create',
                                                        ip=6,
                                                        tenant=tnt,
                                                        shared=shared,
                                                        apicvrf=found.group(1))
	if not self.addscopID:
	    	return 0
        if is_dual_stack():
            if not self.addscopIDv6:
                return 0
	
    def create_subnetpool(self,tnt,shared=False):
        LOG.info(
        "\n#############################################\n"
        "####  Create SubnetPool ONLY for Tenant %s ####\n"
        "###############################################\n"
        %(tnt))
	if shared:
	    spname = subpoolname_shd
	    sub_pool = subpool_shd
	    ads_name=addscopename_shd
            spname_v6 = subpoolname_shd_v6
            ads_name_v6=addscopename_shd_v6
            sub_pool_v6 = subpool_shd_v6
	else:
	    spname = subpoolname
	    sub_pool = subpool
	    ads_name=addscopename
            spname_v6 = subpoolname_v6
            sub_pool_v6 = subpool_v6
            ads_name_v6=addscopename_v6
	self.subpoolID = neutron.subpoolcrud(spname,'create',
                                             address_scope=ads_name,
					     pool=sub_pool,
					     tenant=tnt,
					     shared=shared)
    	if not self.subpoolID:
		return 0
        if is_dual_stack():
           self.subpoolIDv6 = neutron.subpoolcrud(spname_v6,'create',
                                                  address_scope=ads_name_v6,
                                                  pool=sub_pool_v6,
                                                  tenant=tnt,
                                                  shared=shared)
           if not self.subpoolIDv6:
                return 0

    def create_routers(self):
        LOG.info(
        "\n#############################################\n"
        "####  Create Router for both ML2 Tenants   ####\n"
        "###############################################\n"
        )
        self.rtrIDs = {}
        for tnt in [ml2tnt1,ml2tnt2,ml2tnt3]:
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
    
    def attach_router_to_extnw(self,tnt,nonat=False):
        LOG.info(
        "\n#############################################\n"
        "####  Attach %s Router to the External Network ####\n"
        "###############################################\n"
	%(tnt))
	if not nonat:
	    gw = SAUTO_L3OUT1
	else:
	    gw = SAUTO_L3OUT2
 	try:
	    neutron.rtrcrud(self.rtrIDs[tnt], 'set', rtrprop='gateway',
	   		    gw=gw, tenant=tnt)
	except Exception as e:
	    LOG.error('Setting GW for the Router Failed: ' + repr(e))
	    return 0

    def reboot_vms(self, tnt):
        for vm in ML2vms[tnt]:
            neutron.runcmd(
                'nova --os-tenant-name %s reboot %s'
                % (tnt, vm))

    def install_secgroup_rules(self, tnt, default_route = '0.0.0.0/0'):
        # Since VMs are created with 'default' secgroup, hence
        # adding rules to the default secgroup
        cmd = 'source ~/%s && openstack --os-project-name %s project show %s -c id -f value' % (RCFILE, tnt, tnt)
        result = subprocess.check_output(['bash','-c', cmd])
        proj_id = result.split()[0]
        cmd = "source ~/%s && openstack --os-project-name %s security group list | grep %s | awk '{print $2}'"  % (RCFILE, tnt, proj_id)
        result = subprocess.check_output(['bash','-c', cmd])
        secgroup_id = result.split()[0]
        ethertype = '--ethertype IPv4'
        if default_route == "::/0":
            ethertype = '--ethertype IPv6'
        cmd = 'source ~/%s && openstack --os-project-name %s security group rule create --ingress %s --protocol icmp --icmp-type -1 --icmp-code -1 --remote-ip %s %s' % (RCFILE, tnt, ethertype, default_route, secgroup_id)
        subprocess.check_output(['bash','-c', cmd])
        cmd = 'source ~/%s && openstack --os-project-name %s security group rule create --ingress %s --protocol tcp --dst-port 22 --remote-ip %s %s' % (RCFILE, tnt, ethertype, default_route, secgroup_id)
        subprocess.check_output(['bash','-c', cmd])
        cmd = 'source ~/%s && openstack --os-project-name %s security group rule create --ingress %s --protocol tcp --dst-port 80 --remote-ip %s %s' % (RCFILE, tnt, ethertype, default_route, secgroup_id)
        subprocess.check_output(['bash','-c', cmd])

    def install_tenant_vms(self,tnt):
        LOG.info(
        "\n#############################################\n"
        "####  Install VM for the Tenant %s  ####\n"
        "###############################################\n"
	%(tnt))

        self.install_secgroup_rules(tnt, default_route='::/0')
        self.install_secgroup_rules(tnt)
	ml2_vm_ntk_ip[tnt] = {}
        az = neutron.alternate_az(AVZONE)
        for i in range(len(ML2vms[tnt])):
	    ml2_vm_ntk_ip[tnt][ML2vms[tnt][i]] = {}
            try:
                vmcreate = neutron.spawnVM(tnt,
                                           ML2vms[tnt][i],
                                           self.networkIDs[tnt][i],
                                           availzone=az.next()
                                       	   )
                ml2_vm_ntk_ip[tnt][ML2vms[tnt][i]] = {'ips': vmcreate[0],
                                                      'nets': self.networkIDs[tnt][i]}

	    except Exception as e:
                LOG.error('VM Creation for tnt %s Failed: ' %(tnt)+repr(e))
                return 0

    def cleanup_ml2(self):
	for tnt in TNT_LIST_ML2:
	    #Delete VMs for a given ML2 tenant
	    for vm in ML2vms[tnt]:
	        neutron.runcmd(
		'nova --os-tenant-name %s delete %s' %(tnt,vm))
	    #Delete FIPs
	    try:
	        if ML2Fips:
		    for fip in ML2Fips[tnt]:
		        cmd = 'neutron --os-project-name %s floatingip-delete %s' %(tnt,fip)
                        subprocess.check_output(['bash','-c', cmd])
	    except Exception:
		print 'FIPs do not exist for ',tnt
		pass
	    #Delete Router-ports, gateway and router
	    try:
		if self.rtrIDs[tnt]:
                    subnets = ml2Subs[tnt]
                    if is_dual_stack():
                        subnets.extend(ml2SubsV6[tnt])
                    for subnet in subnets:
		        neutron.runcmd(
		        'neutron router-interface-delete %s %s'
			%(self.rtrIDs[tnt],subnet))
		    neutron.runcmd('neutron router-gateway-clear %s'
		    		   %(self.rtrIDs[tnt]))
		    neutron.runcmd('neutron router-delete %s' 
			           %(self.rtrIDs[tnt]))
	    except Exception:
		print 'Router does not for tenant ',tnt
		pass
	    #Delete Networks
  	    for ntk in ml2Ntks[tnt]:
		    neutron.runcmd('neutron net-delete %s' %(ntk))
	#Delete subnetpool,address-scope,external-network
 	for obj in [subpoolname,subpoolname_shd]:
	    try:
	        neutron.runcmd('neutron subnetpool-delete %s'
		           %(obj))
	    except Exception:
	        pass
        if is_dual_stack():
           for obj in [subpoolname_v6,subpoolname_shd_v6]:
               try:
                   neutron.runcmd('neutron subnetpool-delete %s'
                              %(obj))
               except Exception:
                   pass
           for obj in [addscopename_v6,addscopename_shd_v6]:
               try:
                   neutron.runcmd('neutron address-scope-delete %s'
                              %(obj))
               except Exception:
                   pass
	for obj in [addscopename,addscopename_shd]:
	    try:    
	        neutron.runcmd('neutron address-scope-delete %s'
			   %(obj))
	    except Exception:
	        pass
	neutron.runcmd('neutron net-delete %s' % SAUTO_L3OUT1)
	neutron.runcmd('neutron net-delete %s' % SAUTO_L3OUT2)
	#Purge all resource/config if missed by above cleanups
	for tnt in self.ml2tntIDs:
	    neutron.purgeresource(tnt)


class crudGBP(object):
    from libs.gbp_nova_libs import gbpNova
    global tnt1, tnt2, vms, gbpL3p, gbpL2p, ippool,\
	   gbp_nonat_ads, gbp_nonat_sps
    tnt1, tnt2 = TNT_LIST_GBP
    #tnt2 is primarily used for the purpose of NO-NAT
    gbpL3p = 'L3P1' #tnt2 is using it, while tnt1 uses implicit L3P
    gbpL2p = {tnt1 : ['L2P1','L2P2'],
	      tnt2 : ['L2P3']}
    ippool = {tnt1 : '70.70.70.0/24',
              tnt2 : NONATCIDR}
    gbp_nonat_ads = "nonat_ads"
    gbp_nonat_sps = "nonat_sps"
    vms = {}
    vms[tnt1] = GBPvms[tnt1]
    vms[tnt2] = GBPvms[tnt2]

    def create_gbp_tenants(self):
        self.gbptntIDs = neutron.addDelkeystoneTnt(TNT_LIST_GBP, 'create',getid=True)
	from libs.gbp_nova_libs import gbpNova
        self.gbptnt1 = GBPCrud(RESTIP,tenant=tnt1)
        self.gbptnt2 = GBPCrud(RESTIP,tenant=tnt2)
        self.gbpadmin = GBPCrud(RESTIP)
        self.novatnt1 = gbpNova(RESTIP,tenant=tnt1)
        self.novatnt2 = gbpNova(RESTIP,tenant=tnt2)
    
    def create_l2p_l3p(self,tnt):
	if tnt == tnt1:
            LOG.info(
            "\n################################################################\n"
            "## Create Explicit L2Policies, Auto-PTGs & implicit L3Policy for Tenant %s ##\n"
            "##################################################################\n"
	    %(tnt))
            LOG.info(
            "\n## Create L2Policy along with it implicit L3Policy ##\n"
	    )
	    self.l2p1_uuid,self.l2p1_impl3p,self.l2p1_autoptg,self.l2p1_ntkid = \
             self.gbptnt1.create_gbp_l2policy(gbpL2p[tnt1][0],
					      getl3p=True,
					      autoptg=True)
            LOG.info(
            "\n## Create L2Policy explicitly associated to above implicit L3Policy ##\n"
	    )
	    self.l2p2_uuid,self.l2p2_autoptg,self.l2p2_ntkid = \
             self.gbptnt1.create_gbp_l2policy(gbpL2p[tnt][1],
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
	        %(tnt, self.l2p1_impl3p, self.l2p1_uuid, self.l2p1_autoptg,
	        self.l2p2_uuid, self.l2p2_autoptg))
  	if tnt == tnt2:
            LOG.info(
            "\n################################################################\n"
            "## Create Address Scope, Explicit L3Policy, L2Policy for Tenant %s ##\n"
            "##################################################################\n"
	    %(tnt))
	    self.addscopID = neutron.addscopecrud(gbp_nonat_ads,
						'create',
					         shared=True,
						 apicvrf=APICVRF)
	    if self.addscopID:
	        self.subpoolID = neutron.subpoolcrud(gbp_nonat_sps,'create',
                                             address_scope=gbp_nonat_ads,
					     pool=NONATCIDR,
					     shared=True)
    	        if not self.subpoolID:
		    LOG.info("Create of Subnetpool Failed for GBP")
		    return 0
	    else:
		LOG.info("Create of AddressScope Failed for GBP")
		return 0
	    self.l3p_uuid = self.gbptnt2.create_gbp_l3policy(gbpL3p,
					     subnetpools_v4=[self.subpoolID]
						)
	    self.l2p3_uuid,self.l2p3_autoptg,self.l2p3_ntkid = \
             self.gbptnt2.create_gbp_l2policy(gbpL2p[tnt][0],
					      l3_policy_id=self.l3p_uuid,
					      autoptg=True)
	    if not self.l2p3_uuid or not self.l2p3_autoptg:
	         return 0
	    else:
	        LOG.info(
	        "\n## Following resources have been created for Tenant %s:\n"
	        "Explicitly-created L3Policy using AddressScope = %s\n"
	        "Explicit L2Policy = %s and its AutoPTG = %s\n"
	        %(tnt, self.l3p_uuid, self.l2p3_uuid, self.l2p3_autoptg))

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

    def create_policy_target(self,tnt):
	gbp_vm_ntk_ip[tnt]={}
	if tnt == tnt1:
            LOG.info(
            "\n################################################\n"
            "## Create Policy-Targets for two Auto-PTGs and one\n"
            "## Regular PTG for Tenant %s ##\n"
            "##################################################\n"
	    %(tnt))

	#NOTE: 2 PTs/VMs will be created out of self.l2p1_autoptg,
	#so repeating the element in the list, such that this list
	#and the ptlist are of same length
	#VM in sef.regPtg = VM1
	#VMs in self.l2p1_autoptg = VM2 & VM3
	#VM in self.l2p2_autoptg = VM4 
	#NOTE: Since netns needs to be a the property of a VM, needed
	#for traffic, all PTGs in L2P1 will have the same neutron-ntk
	# i.e. self.reg_ptg,self.l2p1_autoptg = self.l2p1_ntkid

	    if self.reg_ptg and self.l2p1_autoptg and self.l2p2_autoptg:
	        self.ptgs = [self.reg_ptg, self.l2p1_autoptg, self.l2p1_autoptg,\
		         self.l2p2_autoptg]
	    else:
	        LOG.error(
		    "Cannot create PTs since some PTGs are not yet initialized"
		     )
	        return 0
            self.vms = GBPvms[tnt1]
	    self.ptlist = ['pt1','pt2','pt3','pt4']
	    for i in range(len(self.ptlist)):
	        pt = self.ptlist[i]
	        vm = self.vms[i]
	        ptg = self.ptgs[i]
	    #NOTE:First all 3 PTs/VMs belong to L2P1 BD
	        if i < 3:
		    if i == 0:
		       tag = 'intra_bd'
		    else:
		       tag = 'intra_epg'
		    ntk = self.l2p1_ntkid
	        else:
	    	    ntk = self.l2p2_ntkid
		    tag = 'inter_bd'
	        gbp_vm_ntk_ip[tnt][vm] = {'port' : self.gbptnt1.create_gbp_policy_target(
       			          pt, ptg, ptg_property='uuid')[1],
				'netns' : 'qdhcp-%s' %(ntk),
				'tag' : tag}
	if tnt == tnt2:
            LOG.info(
            "\n######################################################\n"
            "## Create Two Policy-Targets from an Auto-PTGs for Tenant %s\n"
            "########################################################\n"
	    %(tnt))
	    self.vms = GBPvms[tnt2]
	    for vm,pt in {self.vms[0]:'pt5',self.vms[1]:'pt6'}.iteritems():
	        gbp_vm_ntk_ip[tnt][vm] = {'port' : self.gbptnt2.create_gbp_policy_target(
						   pt,self.l2p3_autoptg,
						   ptg_property='uuid')[1],
					  'netns' : 'qdhcp-%s' %(self.l2p3_ntkid),
					  'tag' : 'intra_epg'
					}
	print gbp_vm_ntk_ip
	if 0 in gbp_vm_ntk_ip.values():
	    LOG.error("\nNot all PTs are created properly = %s"
                 %(gbp_vm_ntk_ip))
	    return 0
    def install_tenant_vms(self,tnt):
        LOG.info(
        "\n################################################\n"
        "## Create VMs for Tenant %s ##\n"
        "##################################################\n"
        %(tnt))
        az = neutron.alternate_az(AVZONE)
        for vm,prop in gbp_vm_ntk_ip[tnt].iteritems():
            vm_image = 'ubuntu_multi_nics'
            vm_flavor = 'm1.medium'
            if conf.get('vm_image'):
                vm_image = conf['vm_image']
            if conf.get('vm_flavor'):
                vm_flavor = conf['vm_flavor']
	    if tnt == tnt1:
                vm_ip = self.novatnt1.vm_create_api(vm,
                                      vm_image,
                                      [{'port-id': prop['port']}],
                                      avail_zone=az.next(),
                                      flavor_name=vm_flavor,
				      ret_ip = True)
	    if tnt == tnt2:
                vm_ip = self.novatnt2.vm_create_api(vm,
                                      vm_image,
                                      [{'port-id': prop['port']}],
                                      avail_zone=az.next(),
                                      flavor_name=vm_flavor,
				      ret_ip = True)
	    if not vm_ip:
                LOG.error("\n//// %s Create failed ////" %(vm))
                return 0
	    else:
		gbp_vm_ntk_ip[tnt][vm]['src_ip'] = vm_ip 
	print "VM_property after VM install == ",gbp_vm_ntk_ip

    def create_ext_seg(self,nattype):
        LOG.info(
        "\n########################################################\n"
        "## Create External Segment as shared under tenant-Admin ##\n"
        "##########################################################\n"
        )
	self.extsegid = {}
	if nattype == 'nat':
	    es_name = SAUTO_L3OUT1
	    extsub = create_external_network_subnets('nat')[0]
	if nattype == 'nonat': 
	    es_name = SAUTO_L3OUT2
	    extsub = create_external_network_subnets('nonat')
        self.extsegid = self.gbpadmin.create_gbp_external_segment(
                                        es_name,
					subnet_id = extsub,
					external_routes = [{
                                           'destination':'0.0.0.0/0',
                                           'nexthop': None}],
				       	shared=True
                                       )
	    
        if self.extsegid == 0:
            LOG.error(
            "\nCreation of %s External Segment %s failed" %(nattype, es_name))
            return 0

    def create_ext_pol(self,tnt):
        LOG.info(
        "\n########################################\n"
        "## Create External Policy in tenant %s ##\n"
        "###########################################\n"
        %(tnt)) 
	if tnt == tnt1:
	    extpolname = L3OUT1_NET
	if tnt == tnt2:
	    extpolname = L3OUT2_NET
	gbptnt = GBPCrud(RESTIP,tenant=tnt)
	self.extpol = gbptnt.create_gbp_external_policy(
					extpolname,
					external_segments=[self.extsegid]
					)
	if self.extpol == 0:
            LOG.error(
            "\nCreation of External Policy failed")
            return 0

    def attach_l3p_extseg(self,tnt):
        LOG.info(
        "\n########################################################\n"
        "## Updating L3Policy in tenant %s to attach to ExtSegments ##\n"
        "##########################################################\n"
        %(tnt))
	if tnt == tnt1:
	    l3p = self.l2p1_impl3p
	if tnt == tnt2:
	    l3p = self.l3p_uuid
	gbptnt = GBPCrud(RESTIP,tenant=tnt)
	if gbptnt.update_gbp_l3policy(l3p,
					    property_type='uuid',
					    external_segments=self.extsegid
					    ) == 0:
            LOG.error(
	    "\nUpdating L3Policy to attach ExtSegment failed for Tenant %s"
	    %(tnt))
	    return 0

    def create_shared_contracts(self):
        LOG.info(
        "\n########################################################\n"
        "## Create shared contracts and related resources in tenant-Admin %s ##\n"
        "##########################################################\n"
        )
	#Create and Verify Policy-Action
        self.gbpadmin.create_gbp_policy_action(ACT,
                                             action_type='allow',
					     shared=True)
        self.actid = self.gbpadmin.verify_gbp_policy_action(ACT)
        if self.actid == 0:
            LOG.error(
		"\n Reqd Policy Action Create Failed")
            return 0
	#Create and Verify Policy-Classifier ICMP
        self.gbpadmin.create_gbp_policy_classifier(CLS_ICMP,
                                                  direction= 'bi',
                                                  protocol = 'icmp',
						  shared=True)
        self.clsicmpid = self.gbpadmin.verify_gbp_policy_classifier(CLS_ICMP)
        if self.clsicmpid == 0:
            LOG.error(
                "\nReqd ICMP Policy Classifier Create Failed")
            return 0
        if is_dual_stack():
            self.gbpadmin.create_gbp_policy_classifier(CLS_ICMPV6,
                                                      direction= 'bi',
                                                      protocol = 58,
                                                     shared=True)
            self.clsicmpidv6 = self.gbpadmin.verify_gbp_policy_classifier(CLS_ICMPV6)
            if self.clsicmpidv6 == 0:
                LOG.error(
                    "\nReqd ICMP Policy Classifier Create Failed")
                return 0
        #Create and Verify Policy-Rule ICMP
        self.gbpadmin.create_gbp_policy_rule(PR_ICMP,
                                            self.clsicmpid,
                                            self.actid,
                                            property_type = 'uuid',
					    shared=True)
        self.ruleicmpid = self.gbpadmin.verify_gbp_policy_rule(PR_ICMP)
        if self.ruleicmpid == 0:
            LOG.error(
                "\n## Reqd ICMP Policy Rule Create Failed")
            return 0
        if is_dual_stack():
            self.gbpadmin.create_gbp_policy_rule(PR_ICMPV6,
                                                self.clsicmpidv6,
                                                self.actid,
                                                property_type = 'uuid',
                                               shared=True)
            self.ruleicmpidv6 = self.gbpadmin.verify_gbp_policy_rule(PR_ICMPV6)
            if self.ruleicmpidv6 == 0:
                LOG.error(
                    "\n## Reqd ICMP Policy Rule Create Failed")
                return 0
        # Create and Verify TCP Policy Classifier
        self.gbpadmin.create_gbp_policy_classifier(CLS_TCP,
                                                  direction= 'bi',
                                                  protocol = 'tcp',
                                                  port_range = '20:2000',
						  shared=True)
        self.clstcpid = self.gbpadmin.verify_gbp_policy_classifier(CLS_TCP)
        if self.clstcpid == 0:
            LOG.error(
                "\nReqd TCP Policy Classifier Create Failed")
            return 0
        # Create and Verify TCP Policy Rule
        self.gbpadmin.create_gbp_policy_rule(PR_TCP,
                                            self.clstcpid,
                                            self.actid,
                                            property_type = 'uuid',
					    shared=True)
        self.ruletcpid = self.gbpadmin.verify_gbp_policy_rule(PR_TCP)
        if self.ruletcpid == 0:
            LOG.error(
                "\n## Reqd TCP Policy Rule Create Failed")
            return 0
	self.prs_name_id = {}
        if is_dual_stack():
            # Create and Verify ICMP-TCP Policy Rule Set
            self.gbpadmin.create_gbp_policy_rule_set(
                                            PRS_ICMP_TCP,
                                            rule_list=[
                                              self.ruleicmpid,
                                              self.ruleicmpidv6,
                                              self.ruletcpid
                                                ],
                                            shared=True,
                                            property_type = 'uuid')
            self.prsicmptcpid = self.gbpadmin.verify_gbp_policy_rule_set(PRS_ICMP_TCP)
            if self.prsicmptcpid == 0:
                LOG.error(
                    "\n## Reqd ICMP-TCP Policy RuleSet Create Failed")
                return 0
            else:
                self.prs_name_id[PRS_ICMP_TCP] = self.prsicmptcpid
        else:
            # Create and Verify ICMP-TCP Policy Rule Set
            self.gbpadmin.create_gbp_policy_rule_set(
                                            PRS_ICMP_TCP,
                                            rule_list=[
                                              self.ruleicmpid,
                                              self.ruletcpid
                                                ],
                                           shared=True,
                                            property_type = 'uuid')
            self.prsicmptcpid = self.gbpadmin.verify_gbp_policy_rule_set(PRS_ICMP_TCP)
            if self.prsicmptcpid == 0:
                LOG.error(
                    "\n## Reqd ICMP-TCP Policy RuleSet Create Failed")
                return 0
            else:
                self.prs_name_id[PRS_ICMP_TCP] = self.prsicmptcpid
        if is_dual_stack():
            # Create and Verify ICMP Policy Rule Set
            self.gbpadmin.create_gbp_policy_rule_set(
                                            PRS_ICMP,
                                            rule_list=[
                                              self.ruleicmpid,
                                              self.ruleicmpidv6
                                                ],
                                            property_type = 'uuid',
                                           shared=True
                                            )
            self.prsicmpid = self.gbpadmin.verify_gbp_policy_rule_set(PRS_ICMP)
            if self.prsicmpid == 0:
                LOG.error(
                    "\n## Reqd ICMP Policy RuleSet Create Failed")
                return 0
            else:
                self.prs_name_id[PRS_ICMP] = self.prsicmpid
        else:
            # Create and Verify ICMP Policy Rule Set
            self.gbpadmin.create_gbp_policy_rule_set(
                                            PRS_ICMP,
                                            rule_list=[self.ruleicmpid],
                                            property_type = 'uuid',
                                           shared=True
                                            )
            self.prsicmpid = self.gbpadmin.verify_gbp_policy_rule_set(PRS_ICMP)
            if self.prsicmpid == 0:
                LOG.error(
                    "\n## Reqd ICMP Policy RuleSet Create Failed")
                return 0
            else:
                self.prs_name_id[PRS_ICMP] = self.prsicmpid
        # Create and Verify TCP Policy Rule Set 
        self.gbpadmin.create_gbp_policy_rule_set(
                                        PRS_TCP,
                                        rule_list=[self.ruletcpid],
                                        property_type = 'uuid',
					shared=True
                                        )
        self.prstcpid = self.gbpadmin.verify_gbp_policy_rule_set(PRS_TCP)
        if self.prstcpid == 0:
            LOG.error(
                "\n## Reqd TCP Policy RuleSet Create Failed")
            return 0
	else:
	    self.prs_name_id[PRS_TCP] = self.prstcpid

    def update_intra_bd_ptg_by_contract(self,prs):
	prs = self.prs_name_id[prs]
	if self.gbptnt1.update_gbp_policy_target_group(
				self.reg_ptg,
				property_type='uuid',
				provided_policy_rulesets=[prs]
				) == 0 or \
	   self.gbptnt1.update_gbp_policy_target_group(
				self.l2p1_autoptg,
				property_type='uuid',
				consumed_policy_rulesets=[prs]
				) == 0:
		return 0

    def update_inter_bd_ptg_by_contract(self,prs):
	prs = self.prs_name_id[prs]
	if self.gbptnt1.update_gbp_policy_target_group(
				self.l2p2_autoptg,
				property_type='uuid',
				provided_policy_rulesets=[prs]
				) == 0:
		return 0
	for ptg in [self.reg_ptg,self.l2p1_autoptg]:
	    if self.gbptnt1.update_gbp_policy_target_group(
				ptg,
				property_type='uuid',
				consumed_policy_rulesets=[prs]
				) == 0:
		return 0
				
    def update_allptgs_by_contract_for_extraff(self,prs):
	prs = self.prs_name_id[prs]
	if self.gbptnt1.update_gbp_external_policy(
				self.extpol,
				property_type='uuid',
				consumed_policy_rulesets=[prs]
				) == 0:
		return 0
	for ptg in [self.reg_ptg,
                    self.l2p1_autoptg,
		    self.l2p2_autoptg]:
	    if self.gbptnt1.update_gbp_policy_target_group(
				ptg,
				property_type='uuid',
				consumed_policy_rulesets=None,
				provided_policy_rulesets=[prs]
				) == 0:
		return 0

    def update_ptg_extptg_nonat_traff(self,prs):
	prs = self.prs_name_id[prs]
	if self.gbptnt2.update_gbp_external_policy(
				self.extpol,
				property_type='uuid',
				consumed_policy_rulesets=[prs]
				) == 0:
		return 0
	if self.gbptnt2.update_gbp_policy_target_group(
				self.l2p3_autoptg,			
				property_type='uuid',
				consumed_policy_rulesets=None,
				provided_policy_rulesets=[prs]
				) == 0:
		return 0

    def cleanup_gbp(self):
	for tnt in TNT_LIST_GBP:
	    #Delete VMs for a given ML2 tenant
	    for vm in GBPvms[tnt]:
	        neutron.runcmd(
		'nova --os-tenant-name %s delete %s' %(tnt,vm))
	    #Delete FIPs
	    try:
	        if GBPFips:
		    for fip in GBPFips[tnt]:
		        cmd = 'neutron --os-project-name %s floatingip-delete %s' %(tnt,fip)
                        subprocess.check_output(['bash','-c', cmd])
            except Exception:
                print 'FIPs do not exist for ',tnt
                pass
	    try:
		gbpclean = GBPCrud(RESTIP,tenant=tnt)
                pt_list = gbpclean.get_gbp_policy_target_list()
            	if len(pt_list):
              	    for pt in pt_list:
                    	gbpclean.delete_gbp_policy_target(pt, property_type='uuid')
           	ptg_list = gbpclean.get_gbp_policy_target_group_list()
           	if len(ptg_list):
              	    for ptg in ptg_list:
                	gbpclean.delete_gbp_policy_target_group(ptg, property_type='uuid')
           	l2p_list = gbpclean.get_gbp_l2policy_list()
           	if len(l2p_list):
              	    for l2p in l2p_list:
                 	gbpclean.delete_gbp_l2policy(l2p, property_type='uuid')
           	l3p_list = gbpclean.get_gbp_l3policy_list()
           	if len(l3p_list) :
                   for l3p in l3p_list:
                 	gbpclean.delete_gbp_l3policy(l3p, property_type='uuid')
           	gbpclean.delete_gbp_network_service_policy()
           	natpool_list = gbpclean.get_gbp_nat_pool_list()
           	if len(natpool_list) :
              	    for natpool in natpool_list:
                 	gbpclean.delete_gbp_nat_pool(natpool)
           	extpol_list = gbpclean.get_gbp_external_policy_list()
           	if len(extpol_list) :
              	    for extpol in extpol_list:
                 	gbpclean.delete_gbp_external_policy(extpol)
           	extseg_list = gbpclean.get_gbp_external_segment_list()
           	if len(extseg_list) :
              	    for extseg in extseg_list:
                 	gbpclean.delete_gbp_external_segment(extseg)
           	prs_list = gbpclean.get_gbp_policy_rule_set_list()
        	if len(prs_list) > 0:
           	    for prs in prs_list:
               		gbpclean.delete_gbp_policy_rule_set(
				   prs, property_type='uuid')
        	pr_list = gbpclean.get_gbp_policy_rule_list()
        	if len(pr_list) > 0:
           	    for pr in pr_list:
               		gbpclean.delete_gbp_policy_rule(
					pr, property_type='uuid')
        	cls_list = gbpclean.get_gbp_policy_classifier_list()
        	if len(cls_list) > 0:
           	    for cls in cls_list:
               		gbpclean.delete_gbp_policy_classifier(
					cls, property_type='uuid')
        	act_list = gbpclean.get_gbp_policy_action_list()
        	if len(act_list) > 0:
           	    for act in act_list:
               		gbpclean.delete_gbp_policy_action(
				act, property_type='uuid')
	    except Exception as e:
		print "Exception in Cleanup == ", repr(e)
		pass
	neutron.runcmd('neutron subnetpool-delete %s' %(gbp_nonat_sps))
	neutron.runcmd('neutron address-scope-delete %s' %(gbp_nonat_ads))
	neutron.runcmd('neutron net-delete %s' % SAUTO_L3OUT1)
	neutron.runcmd('neutron net-delete %s' % SAUTO_L3OUT2)
	#Purge all resource/config if missed by above cleanups
        if self.gbptntIDs:
	    for tnt in self.gbptntIDs:
	    	neutron.purgeresource(tnt)
	return 1

class verifyML2(object):
      def __init__(self):
	return 1


class sendTraffic(object):
    #Ensure to inherit/instantiate the class after 
    #all VMs are created
    def generate_vm_prop(self,tnt,ext=False):
        netns_dict = {}
	print 'VM_to_NTK_IP inside Traffic Class for == ', ml2_vm_ntk_ip[tnt]
  	properties = {}
	for vm,prop in ml2_vm_ntk_ip[tnt].iteritems():
           pingable_ips = []
           for val in ml2_vm_ntk_ip[tnt].values():
                if type(val['ips']) is list:
                    pingable_ips.extend([ip for ip in val['ips']])
                    for ip in val['ips']:
                        netns_dict[ip] = 'qdhcp-'+val['nets']
                else:
                    pingable_ips.extend([val['ips']])
                    netns_dict[ip] = 'qdhcp-'+val['nets']
	   if ext:
               pingable_ips.extend([EXTRTRIP1,EXTRTRIP2])
           #Removing the Src_IPs from the list of pingable_ips
           if type(prop['ips']) is list:
               for ip in prop['ips']:
                   pingable_ips.remove(ip)
           else:
               pingable_ips.remove(prop['ips'])
	   dest_ips = pingable_ips
           properties[vm] = {'netns' : 'qdhcp-'+prop['nets'],
                             'src_ip' : prop['ips'],
			     'dest_ip' : dest_ips
			    }
        return properties, netns_dict
	
    def traff_from_ml2_tenants(self,tnt,ext=False,proto=['icmp','tcp','metadata'],no_ipv6=False):
	LOG.info(
        "\n#############################################\n"
        "## Sending Traffic from VMs in ML2-tenant %s ##\n"
        "###############################################\n"
        %(tnt))
	tenant_vms  = ML2vms[tnt]
        vm_property, netns_dict = self.generate_vm_prop(tnt,ext=ext)
	print "VM Properties == ", vm_property
        failed_traff = 0
	for vm in tenant_vms:
	    vm_traff = gbpExpTraff(COMPUTE1,vm_property[vm]['netns'],
				vm_property[vm]['src_ip'],
                                vm_property[vm]['dest_ip'],
                                netns_dict)
            iter=1
            while True:
               if not vm_traff.run_and_verify_traffic(proto,tcp_syn_only=1,no_ipv6=no_ipv6):
                   iter+=1
                   #Sleep for 5s and re-run traffic again
                   sleep(5)
                   if iter > max_traff_attempts:
                        failed_traff = 1
                        break
               else:
                   break
        if failed_traff:
            return 0
        else:
           return 1

    def get_epg_vms(self,tnt,tag):
	"""
	The intent of this method is to return a dict of VMs
	based on their EPG or BD locations
	"""
	epg_vms = {}
        netns_dict = {}
	if tag == 'intra_epg':
	    for vm,prop in gbp_vm_ntk_ip[tnt].iteritems():
		#NOTE: pingable IPs are ONLY the VM_IPs in the same EPG
                pingable_ips = []
                for val in gbp_vm_ntk_ip[tnt].values():
                    if val['tag'] == tag:
                        if type(val['src_ip']) is list:
                            pingable_ips.extend(val['src_ip'])
                            for ip in val['src_ip']:
                                netns_dict[ip] = val['netns']
                        else:
                            pingable_ips.append(val['src_ip'])
                            netns_dict[ip] = val['netns']
	        if prop['tag'] == tag:
                    if type(prop['src_ip']) is list:
                        for ip in prop['src_ip']:
                            pingable_ips.remove(ip)
                    else:
                        pingable_ips.remove(prop['src_ip'])
		    prop['dest_ip'] = pingable_ips
		    epg_vms[vm] = prop
            return epg_vms, netns_dict
	if tag == 'intra_bd':
	    for vm,prop in gbp_vm_ntk_ip[tnt].iteritems():
		#NOTE: pingable IPs are ONLY the VM_IPs in the same BD
                pingable_ips = []
                for val in gbp_vm_ntk_ip[tnt].values():
                    if val['tag'] == 'intra_epg' or 'intra_bd':
                        if type(val['src_ip']) is list:
                            pingable_ips.extend(val['src_ip'])
                            for ip in val['src_ip']:
                                netns_dict[ip] = val['netns']
                        else:
                            pingable_ips.append(val['src_ip'])
                            netns_dict[ip] = val['netns']
	        if prop['tag'] == tag:
                    if type(prop['src_ip']) is list:
                        for ip in prop['src_ip']:
                            pingable_ips.remove(ip)
                    else:
                        pingable_ips.remove(prop['src_ip'])
		    prop['dest_ip'] = pingable_ips
		    epg_vms[vm] = prop
            return epg_vms, netns_dict
	if tag == 'inter_bd': 
	    #NOTE: pingable IPs are all the VM_IPs in the same 
	    for vm,prop in gbp_vm_ntk_ip[tnt].iteritems():
                pingable_ips = []
                for val in gbp_vm_ntk_ip[tnt].values():
                    if type(val['src_ip']) is list:
                        pingable_ips.extend(val['src_ip'])
                        for ip in val['src_ip']:
                            netns_dict[ip] = val['netns']
                    else:
                        pingable_ips.append(val['src_ip'])
                        netns_dict[ip] = val['netns']
	        if prop['tag'] == tag:
                    if type(prop['src_ip']) is list:
                        for ip in prop['src_ip']:
                            pingable_ips.remove(ip)
                    else:
                        pingable_ips.remove(prop['src_ip'])
		    prop['dest_ip'] = pingable_ips
		    epg_vms[vm] = prop
            return epg_vms, netns_dict
		 
    def traff_from_gbp_tenant(self,tnt,traffic_type,ext=False,
				proto=['icmp','tcp','metadata']
				):
	LOG.info(
        "\n#############################################\n"
        "## Sending Traffic from VMs in GBP-tenant %s ##\n"
        "###############################################\n"
        %(tnt))
	# valid strings for traffic_type:: 'inter_bd', 'intra_bd', 'intra_epg'
        test_vms, netns_dict = self.get_epg_vms(tnt,traffic_type)
	print 'After EPG based classification of VMs ', test_vms	
        failed_traff = 0
	for vm,vm_property in test_vms.iteritems():
	    if ext:
		target_ips = [EXTRTRIP1,EXTRTRIP2]
	    else:
		target_ips = vm_property['dest_ip']
	    print "Target IPs for the VM ", vm, target_ips
	    vm_traff = gbpExpTraff(COMPUTE1,vm_property['netns'],
				vm_property['src_ip'],
                                target_ips, netns_dict)
            iter=1
            while True:
               if not vm_traff.run_and_verify_traffic(proto,tcp_syn_only=1):
                   iter+=1
                   #Sleep for 5s and re-run traffic again
                   sleep(5)
                   if iter > max_traff_attempts:
                        failed_traff = 1
                        break
               else:
                   break
        if failed_traff:
            return 0
        else:
           return 1
	
    def traff_from_extrtr_to_fips(self,mode,tnt):
        """
        Ping and TCP test from external router to VMs
        """
	LOG.info(
        "\n#############################################\n"
        "## Sending ICMP/TCP Traffic from EXT-RTR to VMs ##\n"
        "###############################################\n"
        )
	if mode == 'ml2':
	    fips = ML2Fips[tnt]
	else:
	    fips = GBPFips[tnt]
	print "Target FIPs for the EXT-RTR", fips
        run_traffic = traff_from_extgwrtr(
                                          EXTRTR,
                                          fips
                                          )
        if isinstance(run_traffic, dict):
	    #Sleep for 5s and re-run traffic again
	    sleep(5)
	    if isinstance(run_traffic, dict):
                return 0




