from test_sanity import *

test_conf = crudML2()

tnt1,tnt2 = TNT_LIST_ML2
print tnt1, tnt2

test_conf.create_ml2_tenants()

#Step 1:
test_conf.create_add_scope()

#Step 2:
test_conf.create_subnetpool()

#Step 3:
test_conf.create_pvt_network_subnets()

#Step 4:
test_conf.install_tenant_vms(tnt1)

#Step 5:
test_traff = sendTraffic

