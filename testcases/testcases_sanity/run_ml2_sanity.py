from test_sanity import *
LOG.setLevel(logging.INFO)
tnt1,tnt2 = TNT_LIST_ML2
LOG.info("#### Start of ML2 Sanity for these Tenants == %s , %s #####"
         %(tnt1, tnt2))

#Initialize the ML2 CRUD Class
test_conf = crudML2()

LOG.info("Create Openstack Tenants %s and %s " %(tnt1,tnt2))
test_conf.create_ml2_tenants()

#Step 1:
if test_conf.create_add_scope() == 0:
    LOG.error("ML2-SANITY: Step-1: Create Address-Scope: FAIL")
else:
    LOG.info("ML2-SANITY: Step-1: Create Address-Scope: PASS")

#Step 2:
if test_conf.create_subnetpool() == 0:
    LOG.error("ML2-SANITY: Step-2: Create SubnetPool using Address-Scope: FAIL")
else:
    LOG.info("ML2-SANITY: Step-2: Create SubnetPool using Address-Scope: PASS")

#Step 3:
if test_conf.create_pvt_network_subnets() == 0:
    LOG.error(
    "ML2-SANITY: Step-3: Create Networks, Subnets using Cidrs & subnetpool: FAIL")
else:
    LOG.info(
    "ML2-SANITY: Step-3: Create Networks, Subnets using Cidrs & subnetpool: PASS")

#Step 4: 
if test_conf.create_routers() == 0:
    LOG.error("ML2-SANITY: Step-4: Create Routers for both tenants : FAIL")
else:
    LOG.info("ML2-SANITY: Step-4: Create Routers for both tenants : PASS")

#Step 5:
if test_conf.create_external_network_subnets() == 0:
    LOG.error(
    "ML2-SANITY: Step-5: Create shared External Ntk in Admin-tenant for pre-existing L3Out : FAIL")
else:
    LOG.info(
    "ML2-SANITY: Step-5: Create shared External Ntk in Admin-tenant for pre-existing L3Out : PASS")

LOG.info(
"####### WORKFLOW-1: Attaching router to networks BEFORE VM creation:Tenant %s ######" 
%(tnt1))
#Step 6:
if test_conf.attach_routers_to_networks(tnt1) == 0:
    LOG.error(
    "ML2-SANITY: Step-6: Attach Routers to two networks in tenant %s : FAIL"
     %(tnt1))
else:
    LOG.info(
    "ML2-SANITY: Step-6: Attach Routers to two networks in tenant %s : PASS"
     %(tnt1))

#Step 7: 
if test_conf.attach_router_to_extnw(tnt1) == 0:
    LOG.error(
    "ML2-SANITY: Step-7: Attach router of tenant %s connects to shared External Ntk : FAIL" %(tnt1))
else:
    LOG.info(
    "ML2-SANITY: Step-7: Attach router of tenant %s connects to shared External Ntk : PASS" %(tnt1))

#Step 8:
if test_conf.install_tenant_vms(tnt1) == 0:
    LOG.error("ML2-SANITY: Step-8: Create VMs for tenant %s : FAIL" %(tnt1))
else:
    LOG.info("ML2-SANITY: Step-8: Create VMs for tenant %s : PASS" %(tnt1))

sleep(15)
#Initialize the Traffic Class
test_traff = sendTraffic()

#Step 9:
if test_traff.traff_from_ml2_tenants(tnt1) == 0:
    LOG.error(
    "ML2-SANITY: Step-9: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : FAIL" %(tnt1))
else:
    LOG.info(
    "ML2-SANITY: Step-9: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : PASS" %(tnt1))
    LOG.info(
    "ML2-SANITY: Step-9: VMs in different Networks/EPGs have DHCP addresses in tenant %s : PASS" %(tnt1))
    LOG.info(
    "ML2-SANITY: Step-9: VMs are reachable(ICMP & SSH) from netns(DHCP-server) for tenant %s : PASS" %(tnt1))

#Step 10:
if test_traff.traff_from_ml2_tenants(tnt1,ext=True) == 0:
    LOG.error(
    "ML2-SANITY: Step-10: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : FAIL" %(tnt1))
else:
    LOG.info(
    "ML2-SANITY: Step-10: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt1))

#Step 11:
if test_conf.attach_fip_to_vms(tnt1) == 0:
    LOG.error(
    "ML2-SANITY: Step-11: Attach FIP to VMs in tenant %s : FAIL" %(tnt1))
else:
    LOG.info(
    "ML2-SANITY: Step-11: Attach FIP to VMs in tenant %s : PASS" %(tnt1))
sleep(20) #For FIP to be learned in Fabric
#Step 12:
if test_traff.traff_from_ml2_tenants(tnt1,ext=True) == 0:
    LOG.error(
    "ML2-SANITY: Step-12: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : FAIL" %(tnt1))
else:
    LOG.info(
    "ML2-SANITY: Step-12: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt1))

LOG.info(
"###### WORKFLOW-2: Attaching router to networks AFTER VM creation:Tenant %s ######" 
%(tnt2))
#Step 13:
if test_conf.install_tenant_vms(tnt2) == 0:
    LOG.error("ML2-SANITY: Step-13: Create VMs for tenant %s : FAIL" %(tnt2))
else:
    LOG.info("ML2-SANITY: Step-13: Create VMs for tenant %s : PASS" %(tnt2))
sleep(15) #For VMs to get learned in Fabric
#Step 14:
if test_traff.traff_from_ml2_tenants(tnt2) == 1:
    LOG.error(
    "ML2-SANITY: Step-14: VMs b/w Networks/EPGs must NOT be reachable for tenant %s : FAIL" %(tnt2))
else:
    LOG.info(
    "ML2-SANITY: Step-14: VMs in different Networks/EPGs have DHCP addresses in tenant %s : PASS" %(tnt2))
    LOG.info(
    "ML2-SANITY: Step-14: VMs are reachable(ICMP & SSH) from netns(DHCP-server) for tenant %s : PASS" %(tnt2))
    LOG.info(
    "ML2-SANITY: Step-14: VMs b/w Networks/EPGs must NOT be reachable for tenant %s : PASS" %(tnt2))

#Step 15:
if test_conf.attach_routers_to_networks(tnt2) == 0:
    LOG.error(
    "ML2-SANITY: Step-15: Attach Routers to two networks in tenant %s : FAIL"
     %(tnt2))
else:
    LOG.info(
    "ML2-SANITY: Step-15: Attach Routers to two networks in tenant %s : PASS"
     %(tnt2))

#Step 16:
if test_traff.traff_from_ml2_tenants(tnt2) == 0:
    LOG.error(
    "ML2-SANITY: Step-16: VMs b/w Networks/EPGs are NOT reachable in tenant %s : FAIL" %(tnt2))
else:
    LOG.info(
    "ML2-SANITY: Step-16: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : PASS" %(tnt2))

#Step 17:
if test_conf.attach_router_to_extnw(tnt2) == 0:
    LOG.error(
    "ML2-SANITY: Step-17: Attach router of tenant %s connects to shared External Ntk : FAIL" %(tnt2))
else:
    LOG.info(
    "ML2-SANITY: Step-17: Attach router of tenant %s connects to shared External Ntk : PASS" %(tnt2))

#Step 18:
if test_traff.traff_from_ml2_tenants(tnt2,ext=True) == 0:
    LOG.error(
    "ML2-SANITY: Step-18: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : FAIL" %(tnt2))
else:
    LOG.info(
    "ML2-SANITY: Step-18: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt2))

#Step 19:
if test_conf.attach_fip_to_vms(tnt2) == 0:
    LOG.error(
    "ML2-SANITY: Step-19: Attach FIP to VMs in tenant %s : FAIL" %(tnt2))
else:
    LOG.info(
    "ML2-SANITY: Step-19: Attach FIP to VMs in tenant %s : PASS" %(tnt2))
sleep(20) #FIP to get learned at Fabric
#Step 20:
if test_traff.traff_from_ml2_tenants(tnt1,ext=True) == 0:
    LOG.error(
    "ML2-SANITY: Step-20: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : FAIL" %(tnt2))
else:
    LOG.info(
    "ML2-SANITY: Step-20: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt2))

