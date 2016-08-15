#!/usr/bin/env python
import sys
import re
from time import sleep
from fabric.api import cd, run, env, hide, get, settings
from fabric.context_managers import *
from neutronclient.v2_0 import client as nclient

class neutronPy(object):
    def __init__(self, controllerIp, username='admin', password='noir0123', tenant='admin'):
        cred = {}
        cred['username'] = username
        cred['password'] = password
        cred['tenant_name'] = tenant
        cred['auth_url'] = "http://%s:5000/v2.0/" % controllerIp
        self.client = nclient.Client(**cred)

    def get_router_list(self):
        """ returns list of routers """
        return self.client.list_routers()['routers']

    def get_router_attribute(self, router_name, attribute):
        ret = None
        rl = self.get_router_list()
        for r in rl:
            if r['name'] == router_name:
                if attribute in r.keys():
                    ret = r[attribute]
                    break
        return ret

    def create_net(self, netname):
        cn = {'network': {'name': netname, 'admin_state_up': True}}
        netw = self.client.create_network(body=cn)
        nid = netw['network']['id']
        return nid
   
    def create_subnet(self, name, cidr, netid):
        cn = {'subnets': [{'name': name, 'cidr': cidr, 'ip_version': 4, 'network_id': netid}]}
        snid = self.client.create_subnet(body=cn)
        return snid['subnets'][0]['id']

    def get_network_list(self):
        return self.client.list_networks()['networks']

    def get_network_attribute(self, network_name, attribute):
        ret = None
        nl = self.get_network_list()
        for n in nl:
            if n['name'] == network_name:
                if attribute in n.keys():
                    ret = n[attribute]
                    break
        return ret

    def get_port_list(self):
        return self.client.list_ports()['ports']

    def get_port_by_owner(self, owner):
        ret = None
        for p in self.get_port_list():
            if p['device_owner'] == owner:
                return p['id']
        return ret

    def delete_unwanted_router(self):
        """ 
            get the subnet id of private network of router1 
            very specific for gbp openstack installation
        """
        subnet = self.get_network_attribute('private', 'subnets')[0]
        routerid = self.get_router_attribute('router1', 'id')
        privatenetid = self.get_network_attribute('private','id')
        publicnetid = self.get_network_attribute('public','id')

        if subnet and routerid:
            self.client.remove_interface_router(routerid, {'subnet_id': subnet})
        if routerid:
            self.client.delete_router(routerid)
        if privatenetid:
            self.client.delete_network(privatenetid)
        if publicnetid:
            self.client.delete_network(publicnetid)

class neutronCli(object):

    def __init__(self,controllerIp,username='root',password='noir0123'):
	self.controller = controllerIp
	self.username = username
	self.password = password
	
    def runcmd(self,cmd):
        env.host_string = self.controller
        env.user = self.username
        env.password = self.password
        with settings(warn_only=True):
             run("hostname")
        srcRc = 'source /root/keystonerc_admin'
        print "EXECUTING THE NEUTRON CLI"
        with prefix(srcRc):
		try:
                   _output = run(cmd)
		   return _output
		except:
		   print "Invalid command due to unknown neutron resource"
		   return ''

    def addDelkeystoneTnt(self,tenantList,action):
	'''
	Add/Delete Tenants in Openstack
	action: vlaid strings are 'create','delete'
	'''
	for tnt in tenantList:
	    if action == 'create':
	       cmd1 = 'keystone tenant-create --name %s' %(tnt)
	       cmd2 = 'keystone user-role-add --user admin --tenant %s --role admin' %(tnt)
	       for cmd in [cmd1,cmd2]:
		   self.runcmd(cmd)
	    if action == 'delete':
		cmd = 'keystone tenant-delete --name %s' %(tnt)

    def getuuid(self,cmd_out):
        '''
        Extracts UUID of the neutron object
        '''
	if cmd_out:
            match=re.search("\\bid\\b\s+\| (.*) \|",cmd_out,re.I)
            if match:
               obj_uuid = match.group(1)
               return obj_uuid.rstrip()
	return 0

    def netcrud(self,name,action,\
                tenant='admin',external=False, shared=False):
        if action == 'create':
	   if external:
	        if shared:
	           cmd = 'neutron --os-tenant-name %s net-create %s --router:external --shared' %(tenant,name)
	        else:
	           cmd = 'neutron --os-tenant-name %s net-create %s --router:external' %(tenant,name)
	   else:
	        cmd = 'neutron --os-tenant-name %s net-create %s' %(tenant,name)
	   ntkId = self.getuuid(self.runcmd(cmd))
	   if ntkId:
	       #print 'Output of ID ==\n', ntkId
	       return ntkId
	if action == 'delete':
	   cmd = 'neutron --os-tenant-name %s net-delete %s' %(tenant,name)
           self.runcmd(cmd)

    def subnetcrud(self,name,action,ntkNameId=None,cidr=None,tenant='admin'):
	"""
	Create/Delete subnets for a given tenant
	action: 'create' or 'delete' are the only valid strings to pass
        ntkNameId: name of the netk, mandatory to pass when action == create
        cidr: Mandatory to pass when action == create
        """
	if action == 'create':
	   cmd = 'neutron --os-tenant-name %s subnet-create %s %s --name %s' %(tenant,ntkNameId,cidr,name) 
	   subnetId = self.getuuid(self.runcmd(cmd))
	   if subnetId:
	       return subnetId
	if action == 'delete':
	   cmd = 'neutron --os-tenant-name %s subnet-delete %s' %(tenant,name)	  
	   self.runcmd(cmd)

    def rtrcrud(self,name,action,rtrprop=None,gw=None,subnet=None,tenant='admin'):
        """
 	action: Valid strings are 'create','delete','add','set','clear'
	rtrprop: Valid strings are 'gateway' or 'interface'
	gw: Name or ID of the External Netk. Mandatory param when rtrprop='gateway'
        subnet: Name or ID of the subnet. Mandatory when rtrprop='interface'
        """
 	if rtrprop == 'gateway':
	   cmd = 'neutron --os-tenant-name %s router-gateway-%s %s %s' %(tenant,action,name,gw)
	if rtrprop == 'interface':
	   cmd = 'neutron --os-tenant-name %s router-interface-%s %s subnet=%s' %(tenant,action,name,subnet)
	if rtrprop == None:
	   cmd = 'neutron --os-tenant-name %s router-%s %s' %(tenant,action,name)
	   if action == 'create':
	      rtrId = self.getuuid(self.runcmd(cmd))
	      if rtrId:
	          return rtrId
	self.runcmd(cmd) 	   		
	
    def Stripper(self,cmdout):
	"""
	Not the Las Vegas one
	"""
	_out = cmdout.split('\n')
	final_out = _out[3:len(_out) - 1]
	final_IDlist = [x.strip(' ') for x in [item.strip('|\r') for item in final_out]]
	return final_IDlist

    def deleteAll(self,tenant):
	cmd = 'neutron --os-tenant-name %s router-list -c id' %(tenant)
	cmd_out = self.runcmd(cmd)
	if cmd_out:
	    rtrList = self.Stripper(cmd_out)
	    for rtr in rtrList:
	         rtrout = self.runcmd('neutron --os-tenant-name %s router-port-list %s -c id' %(tenant,rtr))
		 if rtrout:
		    rtrportList = self.Stripper(rtrout)
		    print rtrportList
		    for port in rtrportList:
		        portdelcmd = 'neutron --os-tenant-name %s router-interface-delete %s port="%s"' %(tenant,rtr,port)
			self.runcmd(portdelcmd)
		 self.runcmd('neutron --os-tenant-name %s router-delete %s' %(tenant,rtr))   
	cmdnet = 'neutron --os-tenant-name %s net-list -c id' %(tenant)
	cmdOut = self.runcmd(cmdnet)
	if cmdOut:
		netList = self.Stripper(cmdOut)
	if netList:
	   for net in netList:
		self.runcmd('neutron --os-tenant-name %s net-delete %s' %(tenant,net))

    def spawnVM(self,tenant,vmname,net='',port=''):
        """
        Method for spawning VMs using net-id or port-id
        """
        if net:
           cmd = 'nova --os-tenant-name %s boot %s --image ubuntu_multi_nics --flavor m1.large --nic net-id=%s' %(tenant,vmname,net)
        if port:
           cmd = 'nova --os-tenant-name %s boot %s --image ubuntu_multi_nics --flavor m1.large --nic port-id=%s' %(tenant,vmname,port)
        if self.runcmd(cmd):
	    sleep(10)
	    vmout = self.runcmd('nova --os-tenant-name %s show %s | grep network' %(tenant,vmname))
	    match = re.search("\\b(\d+.\d+.\d+.\d+)\\b.*",vmout,re.I)
	    if match:
		vmip = match.group(1)
		_out = self.runcmd('nova --os-tenant-name %s interface-list %s | grep ACTIVE'\
				   %(tenant,vmname))
		if _out.succeeded:
		    portMAC = re.search(r'(([0-9a-f]{2}:){5}[0-9a-f]{2})',_out,re.I).group()
		    _match = [i.strip(' ') for i in _out.split('|')]
		    portID = _match[_match.index('ACTIVE')+1]
	        return [vmip,portID,portMAC]
	else:
	    return []

