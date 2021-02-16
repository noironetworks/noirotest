#!/usr/bin/env python  
import sys
from fabric.api import cd, run, env, hide, get, settings, local ,put
from fabric.context_managers import *
from testcases.config import conf
from libs.gbp_nova_libs import gbpNova
from libs.gbp_utils import *

KEY_USER = conf.get('keystone_user')
KEY_PASSWORD = conf.get('keystone_password')
CNTRLRIP = conf['controller_ip']
APICIP = conf['apic_ip']
NTKNODE = conf['network_node']
CONTAINERIZED_SERVICES = conf.get('containerized_services')
CONTAINERIZED_CLI = conf.get('containerized_cli', 'docker')

def main():
    setup(CNTRLRIP,APICIP,NTKNODE)

def setup(controller_ip,apic_ip,ntknode,cntlr_user='heat-admin',apic_user='admin',
          apic_pwd = 'noir0123', cntlr_pwd='noir0123'):

    env.host_string = controller_ip
    env.user = cntlr_user
    env.password = cntlr_pwd

    #Step-0.5: Make sure GBP client is installed on the controller
    #cmd = "sudo yum -y install python-gbpclient.noarch"
    #run(cmd)

    #Step-1: Copy the Heat Templates to the Controller
    for heat_templt in ['~/noirotest/testcases/heat_temps/heat_dnat_only.yaml',
			'~/noirotest/testcases/heat_temps/heat_snat_only.yaml',
			'~/noirotest/testcases/heat_temps/preexist_dnat_only.yaml',
			'~/noirotest/testcases/heat_temps/preexist_snat_only.yaml',
			'~/noirotest/testcases/heat_temps/heat_tmpl_regular_dp_tests.yaml',
			'~/noirotest/add_ssh_filter.py'
			]:
         put(heat_templt,'~/')
    if CONTAINERIZED_SERVICES and 'aim' in CONTAINERIZED_SERVICES:
         cmd = "sudo %s ps | grep aim$" % CONTAINERIZED_CLI
         output = run(cmd)
         cid = output.split()[0]
         cmd = "sudo %s exec -i %s /bin/bash -c 'cat > /home/add_ssh_filter.py' < /home/heat-admin/add_ssh_filter.py" % (CONTAINERIZED_CLI, cid)
         run(cmd)
    #Step-2: Restart the below services
    for cmd in ['sudo systemctl restart openstack-nova-api.service',
		'sudo systemctl restart openstack-nova-scheduler.service',
		'sudo systemctl restart openstack-heat-engine.service',
		'sudo systemctl restart openstack-heat-api.service'
               ]:
       if not CONTAINERIZED_SERVICES:
           run(cmd)
       else:
           # For newer releases, it's containerized, so restart the containers
           service = cmd.split()[-1][10:-8].replace('-','_')
           cmd = "sudo %s ps | grep %s$" % (CONTAINERIZED_CLI, service)
           output = run(cmd)
           print(output)
           container_id = output.split()[0]
           cmd = "sudo %s restart %s" % (CONTAINERIZED_CLI, container_id)
           print cmd
           run(cmd)


    #Step-3: Update the Nova-quotas and Enable ACI Route-reflector
    with settings(warn_only=True):
        os_flvr = run('cat /etc/os-release')
        if 'Red Hat' in os_flvr:
            cmd_src = 'source ~/overcloudrc'
	if 'Ubuntu' in os_flvr:
            cmd_src = 'source ~/overcloudrc'
        rr_cmd = 'apic route-reflector-create --ssl --no-secure '+\
                 '--apic-ip %s --apic-username %s --apic-password %s' %(apic_ip,apic_user,apic_pwd)
	with prefix(cmd_src):
            for cmd in ['nova quota-class-update --instances -1 default',
			'nova quota-class-update --ram -1 default',
			'nova quota-class-update --cores -1 default',
			'nova quota-show',
                        rr_cmd]:
		run(cmd)
 
    #Step-4: Add availability zone 
    NOVA_AGG = conf['nova_agg_name']
    AVAIL_ZONE = conf['nova_az_name']
    AZ_COMP_NODE = conf['az_comp_node']
    gbpnova = gbpNova(CNTRLRIP,cntrlr_uname=cntlr_user,cntrlr_passwd=cntlr_pwd,
                      keystone_user=KEY_USER,keystone_password=KEY_PASSWORD)
    try:
    	# Check if Agg already exists then delete
        cmdagg = run_openstack_cli("nova aggregate-list", CNTRLRIP, username=cntlr_user,passwd=cntlr_pwd)
        if NOVA_AGG in cmdagg:
        	print("Residual Nova Agg exits, hence deleting it")
                gbpnova.avail_zone('cli', 'removehost',
                                           NOVA_AGG,
                                           hostname=AZ_COMP_NODE)
                gbpnova.avail_zone('cli', 'delete', NOVA_AGG)
        print("\nCreating Nova Host-aggregate & its Availability-zone")
        agg_id = gbpnova.avail_zone(
                       'cli', 'create', NOVA_AGG, avail_zone_name=AVAIL_ZONE)
    except Exception:
                print(
                    "\n ABORTING THE TESTSUITE RUN,nova host aggregate creation Failed")
                sys.exit(1)
    print(" Agg %s" % (agg_id))
    try:
        print("\nAdding Nova host to availaibility-zone")
        gbpnova.avail_zone('cli', 'addhost', agg_id, hostname=AZ_COMP_NODE)
    except Exception:
        print("\n ABORTING THE TESTSUITE RUN, availability zone creation Failed")
        gbpnova.avail_zone('cli', 'delete', agg_id)  # Cleanup Agg_ID
        sys.exit(1)
   
    #Step-5: Copy the iptools-arping to the network-node of the fabric
    env.host_string = ntknode
    put('~/noirotest/iputils-arping_20121221-4ubuntu1_amd64.deb', '~/')


if __name__ == "__main__":
    main()
    
