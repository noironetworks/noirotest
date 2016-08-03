#!/usr/bin/env python
import sys
import logging
import os
import re
import datetime
import pexpect
import json
import requests
from time import sleep
from commands import *
from fabric.api import cd,run,env, hide, get, settings, local, lcd
from raise_exceptions import *
from passwdlib import *

# Initialize logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
_log = logging.getLogger( __name__ )

_log.setLevel(logging.INFO)
_log.setLevel(logging.DEBUG)

class Gbp_Aci(object):

    def __init__( self ):
      """
      Init def 
      """
      self.err_strings=['Unable','Conflict','Bad Request','Error', 'Unknown','Exception']
      
    def cmd_error_check(self,cmd_output):
        """
        Verifies whether executed cmd has any known error string
        """
        for err in self.err_strings:
            if re.search('\\b%s\\b' %(err), cmd_output, re.I):
               _log.info(cmd_output)
               _log.info("Cmd execution failed! with this Return Error: \n%s" %(err))
               return 0

    def exec_admin_cmd(self,ip,cmd='',passwd='noir0123'):
        env.host_string = ip
        env.user = "admin"
        env.password = passwd
        env.disable_known_hosts = True
        r = run(cmd)
        if r.failed:
            raise ErrorRemoteCommand("---ERROR---: Error running %s on %s as user admin, stderr %s" % (cmd, ip, r.stderr))
        return r

    def get_root_password(self,ip,passwd='noir0123'):
        token = self.exec_admin_cmd(ip,cmd="acidiag dbgtoken",passwd=passwd)
        with lcd('/root/gbpauto/libs'):
           password = local("./getrootpwd.py %s" % token, capture=True)
        print 'Root Password == ',password
        return password

    def exec_root_cmd(self,ip,cmd):
        env.host_string = ip
        env.password = self.get_root_password(ip)
        print env.password
        env.user = "root"
        env.disable_known_hosts = True
        out = run(cmd)
        if out.failed:
            raise ErrorRemoteCommand("---ERROR---: Error running %s on %s as user root, stderr %s" % (cmd,ip,out.stderr))
        return out

    def opflex_proxy_act(self,leaf_ip,act='restart'):
        """
        Function to 'restart', 'stop' & 'start' opflex_proxy
        leaf_ip = IP Address of a Leaf
        act = restart/stop/start
        """
        cmd_ps = 'ps aux | grep svc_ifc_opflexp'
        out = re.search('\\broot\\b\s+(\d+).*/isan/bin/svc_ifc_opflexp',self.exec_root_cmd(leaf_ip,cmd_ps),re.I)
        if out != None:
           pid = int(out.group(1))        
        if act == 'stop':
           cmd_stop = "kill -s SEGV %s" %(pid)
           for i in range(1,8):
               self.exec_root_cmd(leaf_ip,cmd_stop)
               sleep(5)
               out = re.search('\\broot\\b\s+(\d+).*/isan/bin/svc_ifc_opflexp',self.exec_root_cmd(leaf_ip,cmd_ps),re.I)
               if out == None:
                  break
        if act == 'start':
           cmd_start = 'vsh & test reparse 0xf'
           self.exec_root_cmd(leaf_ip,cmd_start)
           sleep(5)
           cmd_chk = 'vsh & show system internal sysmgr service name opflex_proxy'
           if len(re.findall('State: SRV_STATE_HANDSHAKED',self.exec_root_cmd(leaf_ip,cmd_chk))) > 1:
              return 1
        if act == 'restart':
           cmd = "kill -HUP %s" %(pid)
           out = self.exec_root_cmd(leaf_ip,cmd)
        if out.failed:
            raise ErrorRemoteCommand("---ERROR---: Error running %s on %s as user root, stderr %s" % (cmd,leaf_ip,out.stderr))
        print 'Checking whether process got new pid = \n', self.exec_root_cmd(leaf_ip,cmd_ps)
        
        return 1 

    def apic_verify_mos(self,apic_ip,objs,tenant='admin',uname='admin',passwd='noir0123'):
        """
        Function to verify MOs in APIC
        """
        #TODO:Once actual implmentation is done , below code will be discarded
        if not isinstance(objs,list):
           objs = [objs]
        env.host_string = apic_ip
        env.user = uname
        env.password = passwd
        _output = run("ls -ltr /mit/uni/tn-%s" %(tenant))
        for obj in objs:
            regex = re.compile(r"\W%s\W" %(obj))
            if not bool(regex.search(_output)):
                 return 0
        return 1

    def dev_conn_disconn(self,local_ip,rem_ip,action):
        """
        Function to connect/disconnect any device from the local device
        Primarily we are using for disconnecting APIC from Ostack Controller
        local_ip = the ip of the local device from which removte device will be disconn
        rem_ip = the ip of the remote device
        action = 'disconnect' or 'reconnect' are the valid strings
        """
        if action == 'disconnect':
           cmd = "ip route add %s/32 via 127.0.0.1" %(rem_ip)
        elif action == 'reconnect':
           cmd = "ip route del %s/32" %(rem_ip)
        else:
            print "Passing Invalid string for param 'action'"
            return 0
        if local(cmd).succeeded:
               return 1
        else:
               return 0

    def enable_disable_switch_port(self,apic_ip,switch_node_id,action,port):
        """
        Using APIC user can Admin DOWN/UP a Leaf/Spine Port
        switch_node_id :: NodeID of Leaf/Spine
        action:: 'enable' or 'disable'
        port:: Port of the Leaf/Spine
        """
        env.host_string = apic_ip
        env.user = 'admin'
        env.password = 'noir0123'
        if action == 'enable':
           cmd = 'switchport %s switch %s interface %s' %(action,switch_node_id,port)
        if action == 'disable':
           cmd = 'switchport %s switch %s interface %s' %(action,switch_node_id,port)
        _output = run(cmd)
        print _output
        return 1

    def reboot_aci(self,ip,node='leaf'):
        """
        Reboot APIC/Leaf/Spine
        ip:: ip of the aci device to be rebooted
        """
        
        if node == 'apic':
           cmd = 'reload controller 1'
        else:
           cmd = 'system-reboot'
        self.exec_admin_cmd(ip,cmd)
        return 1

    def aciStatus(self,apic_ip,node,nodetype='leaf',status='active'):
        """
        Verify the node status in ACI
        node: leaf or spine's hostname
        """
        cmdout = self.exec_admin_cmd(apic_ip,'acidiag fnvread | grep %s' %(node))
        if re.search('\d+\s+%s\s+[A-Z0-9]+\s+\d+.\d+.\d+.\d+\/32\s+\\b%s\s+\d\s+\\b%s' %(node,nodetype,status),cmdout,re.I) != None:
           return 1
           

class GbpApic(object):
    def __init__(self, addr,mode,apicsystemID='noirolab',username='admin', password='noir0123', ssl=True):
        self.addr = addr
        self.ssl = ssl
        self.user = username
        self.passwd = password
	self.apicsystemID = apicsystemID
	self.mode = mode # pass the arg mode as 'gbp' or 'ml2'
	if self.mode == 'gbp':
               self.appProfile = 'ap-%s_app' %(self.apicsystemID)
        elif self.mode == 'ml2':
               self.appProfile = 'ap-%s' %(self.apicsystemID)
        self.cookies = None
        self.login()

    def url(self, path):
        if self.ssl:
            return 'https://%s%s' % (self.addr, path)

    def login(self):
        data = '{"aaaUser":{"attributes":{"name": "%s", "pwd": "%s"}}}' % (self.user, self.passwd)
        path = '/api/aaaLogin.json'
        req = requests.post(self.url(path), data=data, verify=False)
        if req.status_code == 200:
            resp = json.loads(req.text)
            token = resp["imdata"][0]["aaaLogin"]["attributes"]["token"]
            self.cookies = {'APIC-Cookie': token}
        return req

    def post(self, path, data):
        return requests.post(self.url(path), data=data, cookies=self.cookies, verify=False)

    def get(self,path):
        return requests.get(self.url(path), cookies=self.cookies, verify=False)

    def delete(self,path):
        return requests.delete(self.url(path), cookies=self.cookies, verify=False)

    def getEpgOper(self,tenant):
	"""
        Method to fetch EPG and their Endpoints for a given tenant
        tenant: List, comprising name of tenants
	"""
	if isinstance(tenant,str):
	   tenant = [tenant]
	finaldictEpg = {}
	for tnt in tenant:
	    finaldictEpg[tnt] = {}
            if tnt == 'common':
               apictenant = 'tn-common'
            else:
               apictenant = 'tn-_%s_%s' %(self.apicsystemID,tnt)
	    tenantepgdict = {}
	    pathtenantepg = '/api/node/mo/uni/%s/%s.json?query-target=children&target-subtree-class=fvAEPg'\
                            %(apictenant,self.appProfile)
	    print 'Tenant EPG Path', pathtenantepg
	    reqforepgs = self.get(pathtenantepg)
            tntDetails = reqforepgs.json()['imdata']
  	    for item in tntDetails:
                epgName = item['fvAEPg']['attributes']['name']
		epgDn = item['fvAEPg']['attributes']['dn']
                tenantepgdict[epgDn] = epgName
	    if len(tenantepgdict):
	        for dn,name in tenantepgdict.iteritems():
		    finaldictEpg[tnt][name] = {}
	            pathepfromepg = '/api/node/mo/%s.json?query-target=children&target-subtree-class=fvCEp' %(dn)
	            print 'PATH == ',pathepfromepg
	            reqforeps = self.get(pathepfromepg)
                    epgDetails = reqforeps.json()['imdata']
                    for item in epgDetails:
			finaldictEpg[tnt][name]['status'] = item['fvCEp']['attributes']['lcC'].encode()
			finaldictEpg[tnt][name]['vm'] = item['fvCEp']['attributes']['contName'].encode()
			finaldictEpg[tnt][name]['ip'] = item['fvCEp']['attributes']['ip'].encode()
			finaldictEpg[tnt][name]['encap'] = item['fvCEp']['attributes']['encap'].encode()
			finaldictEpg[tnt][name]['mcastaddr'] = item['fvCEp']['attributes']['mcastAddr'].encode()
        print 'EPG Details == \n', finaldictEpg
	return finaldictEpg
           
    def getBdOper(self,tenant):
	"""
	Method to fetch subnets,their scopes,L3out association
	"""
        if isinstance(tenant,str):
           tenant = [tenant]
        finaldictBD = {}
        for tnt in tenant:
            finaldictBD[tnt] = {}
            if tnt == 'common':
               apictenant = 'tn-common'
            else:
               apictenant = 'tn-_%s_%s' %(self.apicsystemID,tnt)
	    tenantbddict = {}
	    pathtenantbd = '/api/node/mo/uni/%s.json?query-target=children&target-subtree-class=fvBD'\
			   %(apictenant)
	    print 'Tenant BD Path', pathtenantbd
	    reqforbds = self.get(pathtenantbd)
	    tntDetails = reqforbds.json()['imdata']
	    for item in tntDetails:
		bdName = item['fvBD']['attributes']['name'].encode()
		bdDn = item['fvBD']['attributes']['dn'].encode()
		tenantbddict[bdDn] = bdName
	    if len(tenantbddict):
	        for dn,name in tenantbddict.iteritems():
		    finaldictBD[tnt][name] = {}
		    #Fetch Subnets and their Scopes for a given BD
		    pathforbdsubnets = '/api/node/mo/%s.json?query-target=children&target-subtree-class=fvSubnet'\
				       %(dn)
		    reqforsubnets = self.get(pathforbdsubnets)
		    subnetDetails = reqforsubnets.json()['imdata']
		    subnetdict = {}
		    for item in range(len(subnetDetails)):
			subnetdict.setdefault('subnet-%s' %(item),{})['ip'] = subnetDetails[item]['fvSubnet']['attributes']['ip'].encode()
			subnetdict['subnet-%s' %(item)]['scope'] = subnetDetails[item]['fvSubnet']['attributes']['scope'].encode()
		    finaldictBD[tnt][name]['subnets']=subnetdict
		    # Fetch the VRF associated with a given BD
		    print 'DN for VRF == \n', dn
		    pathforvrf = '/api/node/mo/%s.json?query-target=children&target-subtree-class=fvRsCtx' %(dn)
		    reqforvrf = self.get(pathforvrf)
		    vrfDetails = reqforvrf.json()['imdata']
		    if len(vrfDetails):
			finaldictBD[tnt][name]['vrfname'] = vrfDetails[0]['fvRsCtx']['attributes']['tnFvCtxName'].encode()
			finaldictBD[tnt][name]['vrfstate'] = vrfDetails[0]['fvRsCtx']['attributes']['state'].encode()
		    #Fetch L3Out Association for a given BD
		    pathL3OutLink = '/api/node/mo/%s.json?query-target=children&target-subtree-class=fvRsBDToOut' %(dn)
		    reqforL3Out = self.get(pathL3OutLink)
		    L3outDetails = reqforL3Out.json()['imdata']
		    if len(L3outDetails):
		       finaldictBD[tnt][name]['l3outasso'] = L3outDetails[0]['fvRsBDToOut']['attributes']['tnL3extOutName'].encode()
		    else:
		       finaldictBD[tnt][name]['l3outasso'] = ''
		    #Fetch Operational L3Out for a given BD
		    pathL3OutOper = '/api/node/mo/%s.json?rsp-subtree-include=relations&rsp-subtree-class=l3extOut' %(dn)
		    reqforOperL3Out = self.get(pathL3OutOper)
		    OperL3OutDetails = reqforOperL3Out.json()['imdata']
		    try:
		        finaldictBD[tnt][name]['l3outoper'] = OperL3OutDetails[0]['l3extOut']['attributes']['name'].encode()
		    except:
			finaldictBD[tnt][name]['l3outoper'] = ''
	print 'BD Details == \n', finaldictBD
	return finaldictBD

    
    def getL3Out(self,tenant):
	"""
	Method to fetch the L3Out, its associated VRF and External Ntk
	for a given Tenant/s
	"""
        if isinstance(tenant,str):
           tenant = [tenant]
	finaldictL3Out = {}
	for tnt in tenant:
	    finaldictL3Out[tnt] = {}
	    tenantdictL3Out = {}
	    if tnt == 'common':
	       apictenant = 'tn-common'
	    else:
	       apictenant = 'tn-_%s_%s' %(self.apicsystemID,tnt)
	    pathtenantL3Outs = '/api/node/mo/uni/%s.json?query-target=children&target-subtree-class=l3extOut' %(apictenant)
	    print 'Tenant L3Out Path', pathtenantL3Outs
	    reqforL3Outs = self.get(pathtenantL3Outs)
            tntDetails = reqforL3Outs.json()['imdata']
	    for item in tntDetails:
	        l3OutName = item['l3extOut']['attributes']['name'].encode()
		l3OutDn = item['l3extOut']['attributes']['dn'].encode()
		tenantdictL3Out[l3OutDn] = l3OutName
	    if len(tenantdictL3Out):
		for dn,name in tenantdictL3Out.iteritems():
		    finaldictL3Out[tnt][name] = {}
		    #Fetch the VRF associated with the given L3Out
		    print 'DN for VRF == \n', dn
		    pathforL3Outvrf = '/api/node/mo/%s.json?query-target=children&target-subtree-class=l3extRsEctx' %(dn)
		    reqforL3Outvrf = self.get(pathforL3Outvrf)
		    vrfDetails = reqforL3Outvrf.json()['imdata']
		    if len(vrfDetails):
			finaldictL3Out[tnt][name]['vrfname'] = vrfDetails[0]['l3extRsEctx']['attributes']['tnFvCtxName'].encode()
                        finaldictL3Out[tnt][name]['vrfstate'] = vrfDetails[0]['l3extRsEctx']['attributes']['state'].encode()
	print 'L3 Out Details == \n', finaldictL3Out
	return finaldictL3Out

    def getVrfs(self,tenant):
	"""
	Fetch VRF for tenant/s
	"""
        if isinstance(tenant,str):
           tenant = [tenant]
	finalvrfdict = {}
	for tnt in tenant:
	    finalvrfdict[tnt] = []
	    if tnt == 'common':
               apictenant = 'tn-common'
            else:
               apictenant = 'tn-_%s_%s' %(self.apicsystemID,tnt)
            pathtenantvrf = '/api/node/mo/uni/%s.json?query-target=children&target-subtree-class=fvCtx' %(apictenant)
	    reqforvrfs = self.get(pathtenantvrf)
	    tntDetails = reqforvrfs.json()['imdata']
	    for item in tntDetails:
		finalvrfdict[tnt].append(item['fvCtx']['attributes']['name'].encode())
	return finalvrfdict

    def getHyperVisor(self):
        """
        Return Connection Status of the Hypervisors
        """
        path = '/api/node/class/opflexODev.json'
        req = self.get(path)
        details = req.json()['imdata']
        hypervisor = {}
        if len(details):
           for comp in details:
               name = comp['opflexODev']['attributes']['hostName'].encode()
               hypervisor.setdefault(name,{})['status'] = comp['opflexODev']['attributes']['state'].encode()
               hypervisor[name]['domname'] = comp['opflexODev']['attributes']['domName'].encode()
               hypervisor[name]['cntrlname'] = comp['opflexODev']['attributes']['ctrlrName'].encode()
           print hypervisor
        return hypervisor

    def deletetenants(self):
        """
        Deletes all user created tenants on the APIC
        """
        path = '/api/node/mo/uni.json?query-target=subtree&target-subtree-class=fvTenant'
        req = self.get(path)
        tenantlist = []
        for fvtenant in req.json()['imdata']:
            tenantlist.append(fvtenant['fvTenant']['attributes']['dn'])
        for donotdel in ['uni/tn-common','uni/tn-infra','uni/tn-mgmt']:
            tenantlist.remove(donotdel)
        print 'List of Tenants to be deleted ==\n', tenantlist
        for deltnt in tenantlist:
            path = '/api/node/mo/%s.json' %(deltnt)
            self.delete(path)

    def create_add_filter(self,svcepg,tenant='admin'):
        """
        svcepg: Preferably pass a list of svcepgs if more than one
        """
        #Create the noiro-ssh filter with ssh & rev-ssh subjects
        apictenant = 'tn-_%s_%s' %(self.apicsystemID,tenant)
        path = '/api/node/mo/uni/%s/flt-noiro-ssh.json' %(apictenant)
        data = '{"vzFilter":{"attributes":{"dn":"uni/%s/flt-noiro-ssh","name":"noiro-ssh","rn":"flt-noiro-ssh","status":"created"},"children":[{"vzEntry":{"attributes":{"dn":"uni/%s/flt-noiro-ssh/e-ssh","name":"ssh","etherT":"ip","prot":"tcp","sFromPort":"22","sToPort":"22","rn":"e-ssh","status":"created"},"children":[]}},{"vzEntry":{"attributes":{"dn":"uni/%s/flt-noiro-ssh/e-ssh-rev","name":"ssh-rev","etherT":"ip","prot":"tcp","dFromPort":"22","dToPort":"22","rn":"e-ssh-rev","status":"created"},"children":[]}}]}}' %(3*(apictenant,))
        req = self.post(path, data)
        # Add the noiro-ssh filter to every svcepg_contract
        if not isinstance(svcepg,list):
           svcepg = [svcepg]
        for epg in svcepg:
            path = '/api/node/mo/uni/%s/brc-Svc-%s/subj-Svc-%s.json' %(apictenant,epg,epg)
            data = '{"vzRsSubjFiltAtt":{"attributes":{"tnVzFilterName":"noiro-ssh","status":"created"},"children":[]}}'
            req = self.post(path, data)

    def addEnforcedToPtg(self,epg,flag='enforced',tenant='admin'):
        """
        Add Enforced flag to the PTG
        """
        apictenant = 'tn-_%s_%s' %(self.apicsystemID,tenant)
        path = '/api/node/mo/uni/%s/%s/epg-%s.json' %(apictenant,self.appProfile,epg)
        data = '{"fvAEPg":{"attributes":{"dn":"uni/%s/%s/epg-%s","pcEnfPref":"%s"},"children":[]}}' %(apictenant,self.appProfile,epg,flag)
        req = self.post(path, data)
        print req.text

    def enable_disable_switch_port(self,port,leaf_id,action):
        """
        Enable/disable port on the Leaf
        action = 'enable' or 'disable'
        """
        path = '/api/node/mo/uni/fabric/outofsvc.json'
        if action == 'disable':
           data = '{"fabricRsOosPath":{"attributes":{"tDn":"topology/pod-1/paths-%s/pathep-[%s]","lc":"blacklist"},"children":[]}}' %(leaf_id,port)
        if action == 'enable':
           data = '{"fabricRsOosPath":{"attributes":{"dn":"uni/fabric/outofsvc/rsoosPath-[topology/pod-1/paths-%s/pathep-[%s]]","status":"deleted"},"children":[]}}' %(leaf_id,port)
        print data
        req = self.post(path,data)
        print req.text

	    
