from test_sanity import crudGBP

test_steps = crudGBP()
tnt1,tnt2 = TNT_LIST_GBP

#Step 1:
if not test_steps.create_l2p():
   print 'PASS'


