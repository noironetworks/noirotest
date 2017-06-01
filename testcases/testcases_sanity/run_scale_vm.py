#!/usr/bin/env python
import sys
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_nova_libs import gbpNova
from testcases.config import conf
from libs.neutron import *

CNTRLIP = conf['controller_ip']
AVZONE = conf['nova_az_name']
neutron = neutronPy(CNTRLIP)
nova = gbpNova(CNTRLIP)
crud = GBPCrud(CNTRLIP)

def alternate_az():
    "Alternately returns AvailZone for alternate VM placement"
    while True:
	    yield AVZONE
            yield 'nova'
az = alternate_az()

class scale(object):

    def ml2_scale_vm(self):
	network = neutron.create_net('SCALE-NET1')
	neutron.create_subnet('SCALE-SUB',
				'41.41.41.0/24',
				network
				)
	for i in range(0,2):
	    nova.vm_create_api('SCALE-VM','cirros',
			    [{'net-id': network}],
			    flavor_name='m1.tiny',
			    avail_zone='nova',
			    max_count = 20)
					
run = scale()
run.ml2_scale_vm()
"""
for j in range(1, 7):                                                                                      

    tenantName = 'scale_tenant_%s' % (j)
    gbp_crud = GBPCrud(sys.argv[1], tenant=tenantName)

    pt_dict = gbp_crud.get_gbp_policy_target_list()
    print '\nPT Dict == \n', pt_dict

    gbp_nova = gbpNova(sys.argv[1], os_tenant=tenantName)
    
    i = 1
    for pt in pt_dict.itervalues():
        vm_name = '%s_scale_vm_%s' % (j, i)   
        print vm_name
        gbp_nova.vm_create_api(vm_name, 'cirros', pt, 'm1.tiny', 'nova')
        #gbp_nova.vm_delete(vm_name, 'api')
        i = i + 1
"""
