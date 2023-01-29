#!/usr/bin/env python
# Copyright (c) 2016 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys
import os
import logging
import re
import datetime
from time import sleep
from novaclient.client import Client
from libs.gbp_utils import *
from keystoneauth1 import identity
from keystoneauth1 import session


# Initialize logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
_log = logging.getLogger( __name__ )

_log.setLevel(logging.INFO)
_log.setLevel(logging.DEBUG)

class gbpNova(object):

    def __init__(self,controllerIp,cntrlr_uname='heat-admin',cntrlr_passwd='noir0123',
                 keystone_user='admin', keystone_password='noir0123', tenant='admin'):
        self.cntrlrip = controllerIp
        self.username = cntrlr_uname
        self.password = cntrlr_passwd
        self.cred = {}
        self.cred['version'] = '2'
        self.cred['username'] = keystone_user
        self.cred['password'] = keystone_password
        self.cred['project_name'] = tenant
        self.cred['auth_url'] = "http://%s:5000/v2.0/" % self.cntrlrip
        self.cred['auth_url'] = "http://%s:5000/v3/" % self.cntrlrip
        auth = identity.Password(auth_url=self.cred['auth_url'],
                                 username='admin',
                                 password=self.cred['password'],
                                 project_name=self.cred['project_name'],
                                 project_domain_name='Default',
                                 user_domain_name='Default')
        sess = session.Session(auth=auth)

        self.nova = Client("2", session=sess)
        self.err_strings=['Unable','Conflict','Bad Request','Error', 'Unknown','Exception']

    def get_server(self, server_name):
        return self.nova.servers.find(name=server_name)

    def cmd_error_check(self,cmd_out):
        """
        Verifies whether executed cmd has any known error string
        """
        for err in self.err_strings:
            if re.search('\\b%s\\b' %(err), cmd_out, re.I):
               _log.error("Cmd execution failed! with this Return Error: \n%s" %(cmd_out))
               return 0

    def quota_update(self):
        """
        Updates the instances/cores/ram
        """
        cmd_inst = "sed -i 's/quota_instances.*/quota_instances=-1/' /etc/nova/nova.conf"
        cmd_core = "sed -i 's/quota_cores.*/quota_cores=-1/' /etc/nova/nova.conf"
        cmd_ram = "sed -i 's/quota_ram.*/quota_ram=-1/' /etc/nova/nova.conf"
        cmd_sched = "sed -i 's/^#scheduler_max_attempts=.*/scheduler_max_attempts=1/' /etc/nova/nova.conf"
        cmd_restart1 = "service openstack-nova-api restart"
        cmd_restart2 = "service openstack-nova-scheduler restart"
        cmdlist = [cmd_inst,cmd_core,cmd_ram,cmd_sched,\
                   cmd_restart1,cmd_restart2]
        result = run_remote_cli(cmdlist,self.cntrlrip,
                                self.username,
                                self.password,
                                passOnFailure=False, sudo=True)
        if result:
            return 1
        else:
            _log.error('One of Both Nova services did not restart')
            return 0


    def avail_zone(self,method,action,agg_name_id,avail_zone_name='',hostname=''):
        """
        Call Nova API/CLI to create avail-zone
        method='api' or 'cli' << strings to be passed
        action='create','addhost','removehost','delete' << strings to be passed
        For all action except 'create', 'agg_name_id' arg needs to be passed as an integer(id of the agg)
        """

        if action == 'create':
           if method == 'api':
              agg_str = str(self.nova.aggregates.create(agg_name_id,
                                                        avail_zone_name))
              # By default create() returns a class,to get id converting to str() for regex
              t = re.search('<Aggregate: (\d+)>',agg_str,re.I)
              if t:
                 agg_id = t.group(1)
                 return agg_id
           if method == 'cli':
               cmd='nova aggregate-create '+agg_name_id+' '+avail_zone_name
               results = run_openstack_cli([cmd],self.cntrlrip,
                                           username=self.username,
                                           passwd=self.password)
               if results:
                   t = re.search('\\b(\d+)\\b.*\\b%s\\b.*'\
                       %(agg_name_id),results,re.I)
                   if t:
                       agg_id = t.group(1)
                       return agg_id
               else:
                   return 0
        if action == 'delete':
           if method == 'api':
              self.nova.aggregates.delete(agg_name_id)
              return 1
           if method == 'cli':
              cmd='nova aggregate-delete '+agg_name_id
              if not run_openstack_cli([cmd],self.cntrlrip,
                                   username=self.username,
                                   passwd=self.password):
                 return 0
              return 1
        if action == 'addhost':
           if method == 'api':
              self.nova.aggregates.add_host(agg_name_id,hostname)
              return 1
           if method == 'cli':
              cmd='nova aggregate-add-host '+agg_name_id+' %s' %(hostname)
              if not run_openstack_cli([cmd],self.cntrlrip,
                                   username=self.username,
                                   passwd=self.password):
                 return 0
              return 1
        if action == 'removehost':
           if method == 'api':
              self.nova.aggregates.remove_host(agg_name_id,hostname)
              return 1
           if method == 'cli':
              cmd='nova aggregate-remove-host '+agg_name_id+' %s' %(hostname)
              if not run_openstack_cli([cmd],self.cntrlrip,
                                   username=self.username,
                                   passwd=self.password):
                 return 0
              return 1
    

    def add_host_avail_zone(self,hostname,availzone_name):
        """
        Add host to avail_zone
        """
        ## keeping avail_zone_name same as agg_name
        agg_id = self.avail_zone('api','create',availzone_name,avail_zone_name=availzone_name)
        self.nova.aggregates.add_host(agg_id,hostname)
        
    def get_vm_status(self,max_count):
        """
        Fetches and evaluates the status of VMs
        """
        status_try=1
        while True:
            if len(self.nova.servers.list(
                        search_opts={'status': 'Active'}))== \
                        len(self.nova.servers.list()):
                break   
            elif len(self.nova.servers.list(
                                search_opts={'status': 'ERROR'})):
                _log.error("\nFollowing VMs are in ERROR state")
                return 0
            else:
                status_try +=1
                sleep(1*max_count)
                if status_try > 60:
                    _log.error("\nVMs has NO defined state, taking too "\
                                        "long to spwan")
                    return 0
        return 1
        
    def vm_create_api(self,vmname,vm_image,nics,
                      flavor_name='m1.medium',avail_zone='',
                      ret_ip = False, max_count=1,
                      multihomed=False):
        """
        Call Nova API to create VM and check for ACTIVE status
        nics:: For network, user should pass [{'net-id': ntkid}]
                For port, user should pass [{'port-id': portid}]
                In case of multi-home, pass list of values for
        """
        try:
            vm_image = self.nova.glance.find_image(vm_image)
            vm_flavor = self.nova.flavors.find(name=flavor_name)
            if avail_zone:
                self.nova.servers.create(name=vmname,
                                    image=vm_image,
                                    flavor=vm_flavor,
                                    nics=nics,
                                    availability_zone=avail_zone,
                                    max_count=max_count)
            else:
                self.nova.servers.create(name=vmname,
                                    image=vm_image,
                                    flavor=vm_flavor,
                                    nics=nics,
                                    max_count=max_count)
            if not self.get_vm_status(max_count):
                return 0
            if ret_ip:
                vmobject = self.nova.servers.list()
                if max_count > 1: #Incase of scale
                    vm_name_ip = {} #Using it for only scale
                    for instance in vmobject:
                        if multihomed: 
                            ips = [ip.encode('ascii') for _list in \
                                list(instance.networks.values()) for ip in _list]
                        else:
                            ips = list(instance.networks.values())[0][0].encode('ascii')
                        vm_name_ip[instance.name] = ips    
                else:
                    # Ensure an IPv4 address is first in the list
                    def cmp_func(a,b):
                        ipA = netaddr.IPAddress(a)
                        ipB = netaddr.IPAddress(b)
                        if ipA.version == 4:
                            return -1
                        elif ipB.version == 4:
                            return 1
                        else:
                            return 0
                    for instance in vmobject:
                        if vmname == instance.name:
                            sorted_ips = sorted(list(instance.networks.values())[0])
                            return [ip.encode('ascii') for ip in sorted_ips]
                    #        return instance.networks.values()[0][0].encode('ascii')
        except Exception as e:
                _log.error(
                'VM Creation Failed on Exception = %s\n' %(e))
                import traceback; traceback.print_exc(file=sys.stdout)
                return 0
        return 1
                
    def vm_create_cli(self,vmname,vm_image,ports,
                      avail_zone='',tenant=''):
        """
        Creates VM and checks for ACTIVE status
        tenant :: pass explicit tenant-name, if needed
        """
        if not tenant:
            tenant=self.cred['project_id']
        cmd = 'nova --os-tenant-name %s boot --image ' %(tenant)+\
              vm_image+' --flavor m1.medium'
        if isinstance(ports,str):
           ports = [ports]
        for port in ports:
              cmd = cmd +' --nic port-id='+str(port)
        if avail_zone != '':
           cmd = cmd + ' --availability-zone '+avail_zone+' %s' %(vmname)
        else:
           cmd = cmd + ' %s' %(vmname)
        print('\nvmcreate cmd ==', cmd)
        if not run_openstack_cli([cmd],self.cntrlrip,
                              username=self.username,
                              passwd=self.password):
            _log.info("Creation of VM failed using CLI")
            return 0
        sleep(5)
        return self.check_vm_status('create',vmname,tenant=tenant)
                
    def vm_migrate(self, vmname, dest_compute, method='cli', tenant=''):
        """
        Live migrate an Instance
        dest_compute:: fqdn of the compute-node as appears in nova
        method :: 'api' or 'cli'. IFF 'cli', then pass 'tenant'
                  if tenant != 'admin'
        """
        if method=='api':
           vm_obj = self.nova.servers.find(name=vmname)
           try:
              vm_obj.live_migrate(host=dest_compute,
                                  block_migration=True
                                              )
           except Exception as e:
               print('Error on Live Migration: '+repr(e))
               return 0
        else:
           if not tenant:
               tenant=self.cred['project_name']
           cmd = 'nova --os-tenant-name %s live-migration' %(tenant)+\
                 ' --block-migrate %s %s' %(vmname, dest_compute)
           results = run_openstack_cli([cmd],self.cntrlrip,
                                    username=self.username,
                                    passwd=self.password)
        return 1

    def vm_delete(self,vmname,method='cli',tenant=''):
        """
        Delete Instance 
        """
        if method=='api':
           instance = self.nova.servers.find(name=vmname)
           instance.delete()
        else:
           if not tenant:
               tenant=self.cred['project_name']
           cmd = 'nova --os-tenant-name %s delete ' %(tenant)+vmname
           results = run_openstack_cli([cmd],self.cntrlrip,
                                    username=self.username,
                                    passwd=self.password)
        return self.check_vm_status('delete',vmname,tenant=tenant)

    def check_vm_status(self,action,vmname,tenant=''):
        """
        Checks the VM status based on
        action :: 'create' or 'delete'
        """
        
        if not tenant:
            tenant=self.cred['project_id']
        status_try = 1
        while True:
            cmd = 'nova --os-tenant-name %s show ' %(tenant)+vmname
            out = run_openstack_cli([cmd],self.cntrlrip,
                                 username=self.username,
                                 passwd=self.password)
            if action == 'create':
                if out and re.findall('ACTIVE',out) != []:
                    break
                vm_state = 'NOT ACTIVE'
            if action == 'delete':
                if not out:
                   break
                vm_state = 'STILL STALE'
            _log.info(
            "\nRetrying every 5s to check status of VM on %s" %(action))
            sleep(5)
            if status_try > 3:
               _log.error(
               "\nAfter waiting for 50 seconds, VM status is %s" %(vm_state))
               return 0
            status_try +=1
        return 1
        
    def get_floating_ip(self,vmname):
        """
        Returns the Floating IP associated for the vmname
        """
        instance = self.nova.servers.find(name=vmname)
        try:
           floating_ips = []
           floating_ip_class_list = self.nova.floating_ips.findall(instance_id=instance.id) 
           # this returns a list of class FloatingIP for each floating ip
           # of an instance the above list contains many attributes like
           # fixed_ip,pool_id etc, we can use it to fetch those attribute
           # if need be
           for index in range(0,len(floating_ip_class_list)):
               floating_ips.append(floating_ip_class_list[index].ip.encode('ascii'))
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            _log.error('Exception Type = %s, Exception Traceback = %s' %(exc_type,exc_traceback))
            return None
        return floating_ips

    def action_fip_to_vm(self,action,vmname,extsegname=None,vmfip=None):
        """
        Depending on action type caller
        Can associate or disassociate a FIP
        action:: valid strings are 'associate' or 'disassociate'
        extsegname:: Must be passed ONLY in case of 'associate'
        vmfip:: In case of 'disassociate', vmfip MUST be passed
                In case of 'associate', default = None, for method to
                create FIP-pool and dynamically allocate FIPs to VM
        """
        if action == 'associate':
            if not vmfip:
                fip_pools = self.nova.floating_ip_pools.list()
                if len(fip_pools):
                   print('FIP POOLS', fip_pools)
                   for pool in fip_pools:
                       print(pool.name)
                       if extsegname in pool.name:
                          print('MATCH')
                          try:
                              fip = self.nova.floating_ips\
                                    .create(pool=pool.name)
                              self.nova.servers.find(name=vmname)\
                              .add_floating_ip(fip)
                          except Exception:
                              exc_type, exc_value, exc_traceback = sys.exc_info()
                              _log.error(
                              'Dynamic FIP Exception & Traceback = %s\n %s'\
                              %(exc_type,exc_traceback))
                              return 0
                          # Returning the attr of fip(address)
                          # and the fip object itself
                          return fip.ip.encode(),fip
                else:
                    _log.error('There are NO Floating IP Pools')
                    return 0
            else: #statically associate FIP to VM
                try:
                    fips = self.nova.floating_ips.list()
                    if len(fips):
                        for item in fips:
                            if item.ip == vmfip:
                                self.nova.servers.find(name=vmname)\
                                .add_floating_ip(item)
                                return 1
                except Exception:
                   exc_type, exc_value, exc_traceback = sys.exc_info()
                   _log.error(
                   'Static FIP Exception & Traceback = %s\n %s' \
                   %(exc_type,exc_traceback))
                   return 0
                   
        if action == 'disassociate':
           try:
              self.nova.servers.find(name=vmname).remove_floating_ip(vmfip)
           except Exception:
              exc_type, exc_value, exc_traceback = sys.exc_info()
              _log.error('Exception Type = %s, Exception Traceback = %s' %(exc_type,exc_traceback))
              return 0
        return 1

    def delete_release_fips(self,fip=''):
        """
        Run this method ONLY when fips
        are disassociated from VMs
        fip:: pass specific FIP
        """
        try:
           disassociatedFips = self.nova.floating_ips.list()
           if fip:
               for _fip in disassociatedFips:
                   if _fip.ip == fip:
                       self.nova.floating_ips.delete(_fip)
                       break
           else:
               for fip in disassociatedFips:
                   self.nova.floating_ips.delete(fip)
               print("Any Stale FIPs:: ", self.nova.floating_ips.list())
        except Exception:
           exc_type, exc_value, exc_traceback = sys.exc_info()
           _log.error('Exception Type = %s, Exception Traceback = %s' %(exc_type,exc_traceback))
           return 0
        return 1

    def get_any_vm_property(self,vmname,prop='networks'):
        """
        Returns any VM property
        Pass vmname string & the property name string
        """
        try:
           vm = self.nova.servers.find(name=vmname)
           if prop == 'id':
                vm_prop = vm.id.encode('ascii')
           if prop == 'networks':
                vm_prop = list(vm.networks.values())
                # built-in networks method returns a dict in a list.
                # dict's values is again a list of ip addresses
           if prop == 'hostid':
                vm_prop = vm.hostId.encode('ascii')
           if prop == 'port':
                vm_prop = {}
                for key in vm.addresses.keys():
                    #key=networkName to which VM port is attached
                    vm_prop[key.encode()]=[]
                    vm_prop[key.encode()].append(vm.addresses[key][0]['addr'.encode()].encode())
                    vm_prop[key.encode()].append(vm.addresses[key][0]['OS-EXT-IPS-MAC:mac_addr'])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            _log.error('Exception Type = %s, Exception Object = %s' %(exc_type,exc_traceback))
            return 0
        return vm_prop
    
    def get_floating_ips(self,ret=0):
        """
        ret = 0::Returns a dict of VM UUID & FIP
        OR
        Returns a list of FIPs
        """
        try:
           vm_to_fip = {}
           fiplist = []
           for obj in self.nova.floating_ips.list():
               if ret == 0:
                  vm_to_fip[obj.instance_id] = obj.ip
               else:
                  fiplist.append(obj.ip)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            _log.error('Exception Type = %s, Exception Object = %s' %(exc_type,exc_traceback))
            return None
        if ret == 0:
           return vm_to_fip
        else:
           return fiplist
        
    def sshkey_for_vm(self,sshkeyname,method='cli',action='create'):
        """
        Creates and Upload SSH key for VM
        """
        if action=='create':
         if method != 'cli':
           keypath=gensshkey(sshkeyname)
           if not self.nova.keypairs.findall(name=sshkeyname):
              with open(os.path.expanduser(keypath)) as publickey:
                 try:
                    self.nova.keypairs.create(name=sshkeyname, public_key=publickey.read())
                 except Exception:
                     return 0 #SSH Key upload failed
         else:
           #keypath=gensshkey(sshkeyname)
           cmd = 'nova keypair-add '+sshkeyname+' > %s.pem' %(sshkeyname)
           if self.cmd_error_check(getoutput(cmd)) == 0:
              return 0 ##nova generate keypair failed
           cmd = 'chmod 600 %s.pem' %(sshkeyname)
           getoutput(cmd)
        else: #delete
           cmd = 'nova keypair-delete '+sshkeyname
           getoutput(cmd)
        return 1


        
