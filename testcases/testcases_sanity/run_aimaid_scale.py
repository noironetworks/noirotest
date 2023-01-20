#!/usr/bin/python

import string
import random
from testcases.config import conf
from common_sanity_methods import * #Just for logging & neutron class
LOG.setLevel(logging.INFO)

def tenant_create(net_create_func):
    def tenant_net_create():
        tenant_name = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
        neutron.addDelkeystoneTnt(tenant_name, 'create')
        return net_create_func(tenant_name)
    return tenant_net_create

@tenant_create
def net_create(tnt):
    try:
        neutron_api = neutronPy(CNTRLIP,tenant=tnt)
        net = 'net_%s' %(tnt)
        netID = neutron_api.create_net(net)
        #neutron.netcrud(net,'create',tnt)
        subnet = 'subnet_%s' %(net)
        cidr='120.120.120.0/28'
        subnetID = neutron_api.create_subnet(subnet, cidr, netID)
        #neutron.subnetcrud(subnet,
        #                  'create', 
        #                  net, 
        #                  cidr=cidr,
        #                  tenant=tnt)
        LOG.info("Tenant %s , Network %s, Subnet %s created successfully"
             %(tnt,net,subnet))
        #rtr_id = neutron.rtrcrud('RTR1', 'create', tenant=tnt)
        neutron_api.create_router('RTR1')
        #neutron.rtrcrud(rtr_id, 'set', rtrprop='gateway',
        #               gw = 'Management-Out', tenant=tnt)
        neutron_api.router_set_rem_gw('RTR1','set',ext_net_name='Management-Out')
        #neutron.rtrcrud(rtr_id,'add',rtrprop='interface',
        #               subnet=subnet)
        neutron_api.attach_detach_router_subnet('RTR1',subnetID,'add')
    except Exception as e:
        LOG.error("Create Failed: " + repr(e))

if __name__ == "__main__":
    for i in range(50):
        net_create()



