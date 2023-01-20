#!/usr/bin/env python
import sys
from time import sleep
from fabric.api import cd, run, env, hide, get, settings, local
from fabric.context_managers import *
from testcases.config import conf

CNTRLRIP = conf['controller_ip']
APICIP = conf['apic_ip']
NTKNODE = conf['network_node']
COMP2 = conf['compute-2']

def runjob(cntrlrip,comp1ip,comp2ip,username,passwd):
    cntrlr_update_cmd = "yum update -y"+" openstack-heat-gbp python-django-horizon-gbp "\
                         +"openstack-dashboard-gbp openstack-neutron-gbp python-gbpclient "\
                         +"neutron-opflex-agent apicapi neutron-ml2-driver-apic "\
                         +"aci-integration-module"
    remotecmd = "ssh root@%s" %(cntrlrip)
    runcmdlist = ["%s yum makecache" %(remotecmd),\
                  "%s %s" %(remotecmd,cntrlr_update_cmd), \
                  "%s aimctl db-migration upgrade head" %(remotecmd), \
                  "%s systemctl daemon-reload" %(remotecmd), \
                  "%s systemctl restart aim-aid" %(remotecmd), \
                  "%s systemctl restart aim-event-service-polling" %(remotecmd), \
                  "%s systemctl restart aim-event-service-rpc" %(remotecmd), \
                  "%s systemctl restart neutron-server" %(remotecmd)
                 ]
    print("\n\n ////// Update the Packages & Restart Neutron-Server on the Controller //////")
    for cmd in runcmdlist:
        local(cmd)
    for ip in [comp1ip, comp2ip]:
        comp_update_cmd = "ssh root@%s yum update -y agent-ovs libopflex libmodelgbp neutron-opflex-agent" %(ip)
        comp_restart_cmd1 = "ssh root@%s systemctl restart neutron-opflex-agent" %(ip)
        comp_restart_cmd2 = "ssh root@%s systemctl restart agent-ovs" %(ip)
        print("\n\n ////// Update the Packages, Restart Agent-Ovs, Neutron-OpflexAgent on the Comp-node %s //////" %(ip))
        for cm in [comp_update_cmd, comp_restart_cmd1, comp_restart_cmd2]:
            local(cm)
        sleep(10)
        local("ssh root@%s systemctl status neutron-opflex-agent && ssh root@%s systemctl status agent-ovs" %(ip,ip))
    
runjob(CNTRLRIP,NTKNODE,COMP2,'root','noir0123')

