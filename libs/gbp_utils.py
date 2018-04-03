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

import itertools
import os
from prettytable import PrettyTable
import re
import subprocess
import sys
#import HTML
from fabric.api import cd,run,env, hide, get, settings,sudo,local
from fabric.contrib import files
from fabric.context_managers import *
from raise_exceptions import *
from time import sleep
from testcases.config import conf

L3OUT1=conf.get('primary_L3out')
L3OUT1_NET=conf.get('primary_L3out_net')
L3OUT2=conf.get('secondary_L3out')
L3OUT2_NET=conf.get('secondary_L3out_net')

def run_openstack_cli(cmdList,cntrlrip,
                      username='root',passwd='noir0123', do_sudo=False):
    """
    This function enables the user to
    run cli-cmds on openstack env
    cmdList: preferably pass the cmd/set of cmds
             as a list
    """
    env.host_string = cntrlrip
    env.user = username
    env.password = passwd
    if not isinstance(cmdList,list):
       cmdList = [cmdList]
    with settings(warn_only=True):
        os_flvr = run('cat /etc/os-release',quiet=True)
        if 'Red Hat' in os_flvr:
            cmd_src = 'source ~/overcloudrc.v3'
        if 'Ubuntu' in os_flvr:
            cmd_src = 'source ~/overcloudrc.v3'
        with prefix(cmd_src):
            for cmd in cmdList:
                if do_sudo:
                    results = sudo(cmd,quiet=True)
                else:
                    results = run(cmd,quiet=True)
                if not results.succeeded:
		    print "Unsuccessfull cmd-run output, bailing out ==\n",results
   		    return 0
    return results

def run_remote_cli(cmdList,hostip,username,
                   password,passOnFailure=True, do_sudo=False):
    "Run cmd on a remote machine"
    env.host_string = hostip
    env.user = username
    env.password = password
    if not isinstance(cmdList,list):
       cmdList = [cmdList]
    with settings(warn_only=True):
        run("hostname")
        for cmd in cmdList:
            if do_sudo:
                results = do_sudo(cmd)
            else:
                results = run(cmd)
            if not results.succeeded:
                if not passOnFailure:
                    print "Cmd Execution Failed, continue"
   	            pass
                else:
                    print "Cmd execution Failed, bailing out"
                    return 0,results
    return results
 
def upload_files(hostip,username,
                 password,filename,destpath):
    """
    Upload files on a remote machine
    filename:: local file
    destpath:: the path/location in remote m/c
    where the files should be uploaded
    """
    env.host_string = hostip
    env.user = username
    env.password = password
    files.upload_template(filename,destpath) 
     
def get_apic_system_id(hostip,username,password,
                       filename='/etc/neutron/neutron.conf'):
    #NOTE: For aim-aid the filename should be /etc/aim/aim.conf
    cmd = "sed -nre 's/^apic_system_id=(.*)/\\1/p' %s" %(filename)
    apic_aystem_id = run_remote_cli(cmd,hostip,username,password, do_sudo=True)
    if apic_system_id:
      return apic_system_id

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

def action_service(hostIp,service='agent-ovs',
                  action='restart',user='root',pwd='noir0123'):
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

def add_route_in_extrtr(rtrip,route,nexthop,action='add',user='noiro',pwd='noir0123'):
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
			pwd='noir0123',
                        restart=True):
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
             chk_string = sudo('grep -r %s %s' %(pattern,destfile))
             if chk_string.succeeded: #pattern exists, then delete it
                cmd = 'sed -i '+"'/%s/d' " %(pattern)+destfile #delete
                sudo(cmd)
             cmd = 'sed -i '+\
                   "'/%s" %(section)+\
                   '/a '+"%s' " %(pattern)+\
                   destfile
             sudo(cmd)
        if not add:
            if not isinstance(pattern,list):
                pattern = [pattern]
                for pat in pattern:
                    cmd = 'sed -i '+"'/%s/d' " %(pat)+destfile
	            print cmd
                    sudo(cmd)
	if 'neutron' in destfile:
            print "Neutron Conf edited, hence restarting neutron-server"
            if restart:
               sudo('service neutron-server restart')

def preExistingL3Out(controllerIp,
                     destfile,
                     edgenat=False,
                     nonat=False,
                     revert=False,
                     l3out=[L3OUT1, L3OUT2],
                     user='root',
                     pwd='noir0123',
                     restart=True):
    """
    This function is primarily for NAT-Test
    Creates L3Out
    Comments out Existing Config in L3Out Section
    Adds pre-existing config flags
    Restarts neutron-server
    Deletes the L3Out
    Deletes the Pre-existing config flags
    Reverts the Commented out Config in L3OUt Section
    Restarts the neutron-server
    """
    env.host_string = controllerIp
    env.user = user
    env.password = pwd
    def runcmd(cmd):
        results = run(cmd)
        if not results.succeeded:
           print "Cmd Execution Failed, bailing out"
           sys.exit(1)
    with settings(warn_only=True):
        if not isinstance(l3out,list):
            l3out = [l3out]
        if not revert: #Not reverting the config back
            # Commenting Out existing(comes with install)
            # config params for L3Out 
            for extnet in l3out:
                print "Commenting-Out the existing config-flags in %s" %(extnet)
                cmd = "sed -i "+\
                "'/%(L)s/,+6 {/%(L)s/n; /%(L)s/ ! {s/^/#/}}'" %{'L': extnet}+\
                " %s" %(destfile)
                runcmd(cmd)
                # Convert L3Out into pre-existing by adding necessary config options
                print "Adding preexisting config options into the L3Out"
                if extnet == L3OUT1:
                    extEpg = L3OUT1_NET
                if extnet == L3OUT2:
                    extEpg = L3OUT2_NET
                l3outpatterns = [
                             "external_epg=%s" %(extEpg) ,
                             "preexisting=True"
                            ]
                if edgenat:
                    #TBD: 'vlan_range' cannot be static defined here
                    l3outpatterns.append("edge_nat=True")
                    l3outpatterns.append("vlan_range = 1091:1099")
                if nonat:
                    l3outpatterns.append("enable_nat = False")
                for config in l3outpatterns:
                    cmd = "sed -i "+"'/%s/a %s'" %(extnet,config)+" %s" %(destfile)
                    runcmd(cmd)
            if restart:
                run('service neutron-server restart') #Restart Neutron-Server
        if revert:
            print "Reverting to Initial Config of L3Out Section"
            # Removing pre-exixting config options
            for config in ["preexisting",
                           "external_epg",
                           "enable_nat",
                           "edge_nat",
                          ]:
                cmd = "sed -i "+"'/%s/d'" %(config)+" %s" %(destfile)
                run(cmd) #Ignoring what it returns
            # Uncommenting the config options, reverting to Initial Conf
            for extnet in l3out:
                cmdtoUncomment = "sed -i "+\
                "'/%(L)s/,+6 {/%(L)s/n; /%(L)s/ ! {s/#//}}'" %{'L': extnet}+\
                " %s" %(destfile)
                run(cmdtoUncomment)
            if restart:
                run('service neutron-server restart') #Restart Neutron-Server

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
