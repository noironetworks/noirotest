from test_sanity import *

test_steps = crudGBP()
tnt1,tnt2 = TNT_LIST_GBP

#Step 1:
if test_steps.create_l2p() == 0:
   print 'Create L2P, implicit L3P and Auto-Ptg FAIL'
else:
   print 'Create L2P, implicit L3P and Auto-Ptg PASS'
#Step 2:
if test_steps.create_ptg() == 0:
   print 'Create regular PTG using pre-existing L2P FAIL'
else:
   print 'Create regular PTG using pre-existing L2P PASS'

#Step 3:
if test_steps.create_policy_target() == 0:
   print 'Create Policy-Target from Regular and Auto-PTGs FAIL'
else:
   print 'Create Policy-Target from Regular and Auto-PTGs PASS'

#Step 4:
if test_steps.install_tenant_vms() == 0:
    print 'Install VM on Regular and Auto-PTGs FAIL'
else:
    print 'Install VM on Regular and Auto-PTGs PASS'

