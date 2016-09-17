#!/usr/bin/env python
import sys, time
import paramiko
import subprocess
import re
import os
import sys
import json
import requests
import itertools
#import HTML
from prettytable import PrettyTable
from Crypto.PublicKey import RSA
from raise_exceptions import *
from fabric.api import cd,run,env, hide, get, settings,sudo
from fabric.contrib import files
from time import sleep

def report_table(suitename):
    ps = subprocess.Popen(['grep', '-r', 'TESTCASE', '/tmp/%s.log' %(suitename)], stdout=subprocess.PIPE)
    outPut = ps.communicate()[0]
    #print outPut
    outPut = outPut.splitlines()
    line = 0
    tc_dict = {}
    while line < len(outPut):
        find1 = re.search('\\b(TESTCASE_GBP_.*)\\b: (.*)' , outPut[line], re.I)
        if find1 != None:
           line += 1
           if line <= len(outPut) - 1:
              find2 = re.search('\\b%s\\b: (.*)' %(find1.group(1)), outPut[line],re.I)
              if find2 != None:
                 tc_dict[find1.group(1)]=find2.group(1), find1.group(2)
        line += 1
    #print tc_dict
    table = PrettyTable(["TESTCASE_ID", "RESULTS", "TESTCASE_HEADER"])
    table.padding_width = 1
    for key,val in tc_dict.iteritems():
        table.add_row(["%s" %(key),"%s" %(val[0]),"%s" %(val[1])])
    return table

def report_results(suitename,txt_file):
    orig_stdout = sys.stdout
    f = open('%s' %(txt_file),'a')
    sys.stdout = f
    report=report_table(suitename)
    print report
    sys.stdout = orig_stdout
    f.close()

def gen_tc_header():
    comb_list = [['same_leaf','two_leafs'],['same_host','two_hosts'],['same_ptg','two_ptgs'],\
                  ['same_L3_subnet','two_L3_subnets'],['same_L2_bd','two_L2_bds']]

    out_hdr_list=list(itertools.product(*comb_list))
    out_headers = []
    for hdr in out_hdr_list:
        header = 'test_'+'_'.join(str(i) for i in hdr)
        out_headers.append(header)
    #proto = map(list,list(itertools.combinations(['icmp','tcp','udp','dhcp','arp'],2)))
    proto = list(itertools.combinations(['icmp','tcp','udp','dhcp','arp'],2))
    proto_hdrs = []
    for hdr in proto:
        proto_header = '_'.join(str(i) for i in hdr)
        proto_hdrs.append(proto_header)
    in_hdrs = list(itertools.product(out_headers,proto_hdrs))
    final_headers = []
    for hdr in in_hdrs:
        tc_header = '_'.join(str(i) for i in hdr)
        final_headers.append(tc_header)
    table = PrettyTable(["TESTCASE_ID", "STATUS", "TESTCASE_HEADER"])
    table.padding_width = 1
    for i in range(len(final_headers)):
        table.add_row(["TESTCASE_DP_%s" %(i+1),"TBA","%s" %(final_headers[i])])
    print table

'''
def gen_test_report(test_results,suite,w_or_a):
    """
    The function generates HTML Test Report
    ::test_results: This should be a dict
                    comprising TC_name and Result
    ::suite: TestSuite Name, will be used as Header
    ::w_or_a: 'w'(write new file) or 'a'(append)
    The function needs the installation of custom HTML lib
    http://www.decalage.info/python/html
    """
    # Open an HTML file to show the output in a browser
    HTMLFILE='/root/noiro_test_report.html'
    f = open(HTMLFILE, '%s' %(w_or_a))
    result_colors = {
              'PASS': 'green',
              'FAIL': 'red'
               }

    table = HTML.Table(header_row = ['%s' %(suite), 'Result'])
    for test_id in sorted(test_results):
        # create the colored cell:
        color = result_colors[test_results[test_id]]
        colored_result = HTML.TableCell(test_results[test_id], bgcolor=color)
        # append the row with two cells:
        table.rows.append([test_id, colored_result])
    htmlcode = str(table)
    #print htmlcode
    f.write(htmlcode)
    f.write('<p>')
    f.close()
'''

def del_netns(net_node_ip,netns=[]):
        """
        Deletes the Network Node's Ntk NameSpace
        Associated with every VM
        """
        env.host_string = net_node_ip
        env.user = 'root'
        env.password = 'noir0123'
        run("neutron-netns-cleanup")
        if netns == []:
         with settings(warn_only=True):
                run("neutron-netns-cleanup")
                result = run("ip netns | grep qdhcp")
                netns = [x.strip() for x in result.split('\n')]
        for ns in netns:
           with settings(warn_only=True):
               result = run("ip netns delete %s" %(ns))

class Apic(object):
    def __init__(self, addr, user, passwd, ssl=True):
        self.addr = addr
        self.ssl = ssl
        self.user = user
        self.passwd = passwd
        self.cookies = None
        self.login()

    def url(self, path):
        if self.ssl:
            return 'https://%s%s' % (self.addr, path)
        #return 'http://%s%s' % (self.addr, path)

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
        path = '/api/node/mo/uni.json?query-target=subtree&target-subtree-class=fvTenant'
        return requests.get(self.url(path), cookies=self.cookies, verify=False)
    
    def delete(self,path):
        return requests.delete(self.url(path), cookies=self.cookies, verify=False)

def deletetenants(apicIp,username='admin',password='noir0123'):
    """
    Deletes all user created tenants on the APIC
    """
    path = '/api/node/mo/uni.json?query-target=subtree&target-subtree-class=fvTenant'
    apic = Apic(apicIp,username,password)
    req = apic.get(path)
    tenantlist = []
    for fvtenant in req.json()['imdata']:
        tenantlist.append(fvtenant['fvTenant']['attributes']['dn'])
    for donotdel in ['uni/tn-common','uni/tn-infra','uni/tn-mgmt']:
        tenantlist.remove(donotdel)
    print 'List of Tenants to be deleted ==\n', tenantlist
    for deltnt in tenantlist:
        path = '/api/node/mo/%s.json' %(deltnt)
        apic.delete(path)

def create_add_filter(apicIp,svcepg,username='admin',password='noir0123',tenant='_noirolab_admin'):
        """
        svcepg: Preferably pass a list of svcepgs if more than one
        """
        apic = Apic(apicIp,username,password)

        #Create the noiro-ssh filter with ssh & rev-ssh subjects

        path = '/api/node/mo/uni/tn-%s/flt-noiro-ssh.json' %(tenant)
        data = '{"vzFilter":{"attributes":{"dn":"uni/tn-%s/flt-noiro-ssh","name":"noiro-ssh","rn":"flt-noiro-ssh","status":"created"},"children":[{"vzEntry":{"attributes":{"dn":"uni/tn-%s/flt-noiro-ssh/e-ssh","name":"ssh","etherT":"ip","prot":"tcp","sFromPort":"22","sToPort":"22","rn":"e-ssh","status":"created"},"children":[]}},{"vzEntry":{"attributes":{"dn":"uni/tn-%s/flt-noiro-ssh/e-ssh-rev","name":"ssh-rev","etherT":"ip","prot":"tcp","dFromPort":"22","dToPort":"22","rn":"e-ssh-rev","status":"created"},"children":[]}}]}}' %(tenant,tenant,tenant)
        req = apic.post(path, data)
        print req.text

        # Add the noiro-ssh filter to every svcepg_contract
        if not isinstance(svcepg,list):
           svcepg = [svcepg]
        for epg in svcepg:
            path = '/api/node/mo/uni/tn-%s/brc-Svc-%s/subj-Svc-%s.json' %(tenant,epg,epg)
            data = '{"vzRsSubjFiltAtt":{"attributes":{"tnVzFilterName":"noiro-ssh","status":"created"},"children":[]}}'
            req = apic.post(path, data)
            print req.text

def action_service(hostIp,service='agent-ovs',action='restart',user='root',pwd='noir0123'):
        """
        Action = Stop,Start,Restart on Any Service
        """
        env.host_string = hostIp
        env.user = user
        env.password = pwd
        with settings(warn_only=True):
                restart = run("service %s %s" %(service,action))
                sleep(5)
                if restart.succeeded:
                   if run("systemctl status agent-ovs.service" ).find("active (running)") < 0:
                      print 'ERROR: OpflexAgent is NOT ACTIVE or Running on Restart'
                      return 0
        return 1   

def addEnforcedToPtg(apic_ip,epg,flag='enforced',username='admin',password='noir0123',tenant='_noirolab_admin'):
    """
    Add Enforced flag to the PTG
    """
    apic = Apic(apic_ip,username,password)
    path = '/api/node/mo/uni/tn-%s/ap-noirolab_app/epg-%s.json' %(tenant,epg)
    data = '{"fvAEPg":{"attributes":{"dn":"uni/tn-_noirolab_admin/ap-noirolab_app/epg-%s","pcEnfPref":"%s"},"children":[]}}' %(epg,flag)
    req = apic.post(path, data)
    print req.text

def enable_disable_switch_port(port,leaf_id,action,apicIp,username='admin',password='noir0123'):
    """
    Enable/disable port on the Leaf
     action = 'enable' or 'disable'
    """
    apic = Apic(apicIp,username,password)
    path = '/api/node/mo/uni/fabric/outofsvc.json'
    if action == 'disable':
       data = '{"fabricRsOosPath":{"attributes":{"tDn":"topology/pod-1/paths-%s/pathep-[%s]","lc":"blacklist"},"children":[]}}' %(leaf_id,port)
    if action == 'enable':
       data = '{"fabricRsOosPath":{"attributes":{"dn":"uni/fabric/outofsvc/rsoosPath-[topology/pod-1/paths-%s/pathep-[%s]]","status":"deleted"},"children":[]}}' %(leaf_id,port)
    print data
    req = apic.post(path,data)
    print req.text

def add_route_in_extrtr(rtrip,route,nexthop,action='add',ostype='ubuntu',user='noiro',pwd='noir0123'):
    """
    Adding Routes in ExtRtr(Ubuntu)
    """
    env.host_string = rtrip
    env.user = user
    env.password = pwd
    env.sudo_user = user
    #env.sudo_prompt = '[sudo] password for %s:' %(user)
    #print env.password
    """
    with settings(sudo_user=env.user):
         #run("sudo -s")
         if action == 'add':
            sudo("echo hello")
            sudo("ip route add %s via %s" %(route,nexthop),shell=False)
         if action == 'update':
            sudo("ip route del %s" %(route))
            sudo("ip route add %s via %s" %(route,nexthop))
    """
    if action == 'add':
       with settings(sudo_user='noiro'):
            sudo("ip route")
            print env
            sudo("ip route add %s via %s" %(route,nexthop),shell=False)
            #run("sudo ip route add %s via %s" %(route,nexthop),pty=False)
            #run('noir0123')
    if action == 'update':
            sudo("ip route del %s" %(route))
            sudo("ip route add %s via %s" %(route,nexthop))

def editneutronconf(controllerIp,
                        destfile,
                        pattern,
			add=True,
			section='ml2_cisco_apic',
		   	user='root',
			pwd='noir0123'):
    """
    Add host_pool_cidr config flag and restarts neutron-server
    destfile :: name with location of the file in which
                section is defined
    pattern :: The pattern to match under the above section
    add :: default action is add a pattern, else will remove
           Also if add=True, we need to pass section
    section :: Needs to be provided when needed

    P.S. If there is an existing host_pool_cidr, then it will
    over-riden
    """
    env.host_string = controllerIp
    env.user = user
    env.password = pwd
    with settings(warn_only=True):
	if add:
             chk_string = run('grep -r %s %s' %(pattern,destfile))
             if chk_string.succeeded: #pattern exists, then delete it
                cmd = 'sed -i '+"'/%s/d' " %(pattern)+destfile #delete
                run(cmd)
             cmd = 'sed -i '+\
                   "'/%s" %(section)+\
                   '/a '+"%s' " %(pattern)+\
                   destfile
        if not add:
               cmd = 'sed -i '+"'/%s/d' " %(pattern)+destfile
	print cmd
        run(cmd)
	if 'neutron' in destfile:
            print "Neutron Conf edited, hence restarting neutron-server"
            run('service neutron-server restart')

def PauseToDebug():
    while True:
          try:
               print '\nDo you want to live debug, then hit CNTRL C, decide in next 20 secs'
               sleep(20)
          except KeyboardInterrupt:
               print '\nPausing...  (Hit ENTER to continue, type quit to exit live debug.)'
               response = raw_input()
               if response.lower() == 'quit':
                     break
