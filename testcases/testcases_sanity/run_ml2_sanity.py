from test_sanity import *

test_steps = crudML2()
tnt1,tnt2 = TNT_LIST_ML2

#Step 1:
test_steps.create_pvt_network_subnets()

#Step 2:
test_steps.install_tenant_vms(tnt1)

#Step 3:

