#!/usr/bin/env python  
import sys
from fabric.api import cd, run, env, hide, get, settings, local ,put
from fabric.context_managers import *
from testcases.config import conf
from libs.gbp_nova_libs import gbpNova
from libs.gbp_utils import *

CNTRLRIP = conf['controller_ip']
APICIP = conf['apic_ip']


def main():
    check_ssh = raw_input(
               'Passwordless ssh setup to nodes done(YES/NO): ')
    if check_ssh == 'NO':
	print ('ENSURE to SETUP Passwordless SSH to nodes in your setup')
	sys.exit(0)
    setup(CNTRLRIP,APICIP)

def setup(controller_ip,apic_ip,cntlr_user='root',apic_user='admin',
          apic_pwd = 'noir0123', cntlr_pwd='noir0123'):

    env.host_string = controller_ip
    env.user = cntlr_user
    env.password = cntlr_pwd
  
    #Step-1: Copy the Heat Templates to the Controller
    for heat_templt in ['~/noirotest_local/testcases/heat_temps/heat_dnat_only.yaml',
			'~/noirotest_local/testcases/heat_temps/heat_snat_only.yaml',
			'~/noirotest_local/testcases/heat_temps/preexist_dnat_only.yaml',
			'~/noirotest_local/testcases/heat_temps/preexist_snat_only.yaml',
			'~/noirotest_local/testcases/heat_temps/heat_tmpl_regular_dp_tests.yaml',
			'add_ssh_filter.py'
			]:
         put(heat_templt,'~/')
    #Step-2: Restart the below services
    for cmd in ['systemctl restart openstack-nova-api.service',
		'systemctl restart openstack-nova-scheduler.service',
		'systemctl restart openstack-heat-engine.service',
		'systemctl restart openstack-heat-api.service'
               ]:
       run(cmd)

    #Step-3: Update the Nova-quotas and Enable ACI Route-reflector
    with settings(warn_only=True):
        os_flvr = run('cat /etc/os-release')
        if 'Red Hat' in os_flvr:
            cmd_src = 'source /root/keystonerc_admin'
	if 'Ubuntu' in os_flvr:
            cmd_src = 'source ~/openrc'
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
    gbpnova = gbpNova(CNTRLRIP)
    try:
    	# Check if Agg already exists then delete
        cmdagg = run_openstack_cli("nova aggregate-list", CNTRLRIP)
        if NOVA_AGG in cmdagg:
        	print("Residual Nova Agg exits, hence deleting it")
                gbpnova.avail_zone('cli', 'removehost',
                                           NOVA_AGG,
                                           hostname=AZ_COMP_NODE)
                gbpnova.avail_zone('cli', 'delete', NOVA_AGG)
        print("\nCreating Nova Host-aggregate & its Availability-zone")
        agg_id = gbpnova.avail_zone(
                       'api', 'create', NOVA_AGG, avail_zone_name=AVAIL_ZONE)
    except Exception:
                print(
                    "\n ABORTING THE TESTSUITE RUN,nova host aggregate creation Failed")
                sys.exit(1)
    print(" Agg %s" % (agg_id))
    try:
        print("\nAdding Nova host to availaibility-zone")
        gbpnova.avail_zone('api', 'addhost', agg_id, hostname=AZ_COMP_NODE)
    except Exception:
        print("\n ABORTING THE TESTSUITE RUN, availability zone creation Failed")
        gbpnova.avail_zone('cli', 'delete', agg_id)  # Cleanup Agg_ID
        sys.exit(1)


if __name__ == "__main__":
    main()
    
