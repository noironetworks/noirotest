from test_sanity import *
LOG.setLevel(logging.INFO)
tnt1,tnt2 = TNT_LIST_ML2
LOG.info("#### Start of ML2 Sanity for these Tenants == %s , %s #####"
         %(tnt1, tnt2))

#Initialize the ML2 CRUD Class
test_conf = crudML2()

LOG.info("Create Openstack Tenants %s and %s " %(tnt1,tnt2))
test_conf.create_ml2_tenants()

### Every Step is a Test by itself, so it will log as Test instead of Step ###

try:
    #Step 1:
    if test_conf.create_add_scope(tnt2) == 0:
        raise TestError("ML2-SANITY: Test-1: Create Address-Scope")
    else:
        LOG.info("ML2-SANITY: Test-1: Create Address-Scope: PASS")

    #Step 2:
    if test_conf.create_subnetpool(tnt2) == 0:
        raise TestError("ML2-SANITY: Test-2: Create SubnetPool using Address-Scope")
    else:
        LOG.info("ML2-SANITY: Test-2: Create SubnetPool using Address-Scope: PASS")

    #Step 3:
    if test_conf.create_pvt_network_subnets() == 0:
        raise TestError(
        "ML2-SANITY: Test-3: Create Networks, Subnets using Cidrs & subnetpool")
    else:
    	LOG.info(
    	"ML2-SANITY: Test-3: Create Networks, Subnets using Cidrs & subnetpool: PASS")

    #Step 4: 
    if test_conf.create_routers() == 0:
        raise TestError("ML2-SANITY: Test-4: Create Routers for both tenants ")
    else:
        LOG.info("ML2-SANITY: Test-4: Create Routers for both tenants : PASS")

    #Step 5:
    if create_external_network_subnets('nat') == 0:
        raise TestError(
        "ML2-SANITY: Test-5: Create shared External Ntk in Admin-tenant for pre-existing L3Out ")
    else:
        LOG.info(
        "ML2-SANITY: Test-5: Create shared External Ntk in Admin-tenant for pre-existing L3Out : PASS")

    LOG.info(
    "####### WORKFLOW-1: Attaching router to networks BEFORE VM creation:Tenant %s ######" 
    %(tnt1))
    #Step 6:
    if test_conf.attach_routers_to_networks(tnt1) == 0:
    	raise TestError(
    	"ML2-SANITY: Test-6: Attach Routers to two networks in tenant %s "
     	%(tnt1))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-6: Attach Routers to two networks in tenant %s : PASS"
     	%(tnt1))

    #Step 7: 
    if test_conf.attach_router_to_extnw(tnt1) == 0:
    	raise TestError(
    	"ML2-SANITY: Test-7: Attach router of tenant %s connects to shared External Ntk "
     	%(tnt1))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-7: Attach router of tenant %s connects to shared External Ntk : PASS"
    	%(tnt1))

    #Step 8:
    if test_conf.install_tenant_vms(tnt1) == 0:
    	raise TestError("ML2-SANITY: Test-8: Create VMs for tenant %s " %(tnt1))
    else:
    	LOG.info("ML2-SANITY: Test-8: Create VMs for tenant %s : PASS" %(tnt1))

    sleep(15)
    #Initialize the Traffic Class
    test_traff = sendTraffic()

    #Step 9:
    if test_traff.traff_from_ml2_tenants(tnt1) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-9: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s " %(tnt1))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-9: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : PASS" %(tnt1))
    	LOG.info(
    	"ML2-SANITY: Test-9: VMs in different Networks/EPGs have DHCP addresses in tenant %s : PASS" %(tnt1))
    	LOG.info(
    	"ML2-SANITY: Test-9: VMs are reachable(ICMP & SSH) from netns(DHCP-server) for tenant %s : PASS" %(tnt1))
    	LOG.info(
    	"ML2-SANITY: Test-9: MetaData for VMs in tenant %s : PASS" %(tnt1))

    #Step 10:
    if test_traff.traff_from_ml2_tenants(tnt1,ext=True,proto=['icmp','tcp']) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-10: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr " %(tnt1))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-10: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt1))

    #Step 11:
    if attach_fip_to_vms(tnt1,'ml2') == 0:
    	raise TestError(
    	"ML2-SANITY: Test-11: Attach FIP to VMs in tenant %s " %(tnt1))
    else:
   	LOG.info(
    	"ML2-SANITY: Test-11: Attach FIP to VMs in tenant %s : PASS" %(tnt1))
    sleep(20) #For FIP to be learned in Fabric
    #Step 12:
    if test_traff.traff_from_ml2_tenants(tnt1,ext=True,proto=['icmp','tcp']) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-12: Using FIP VMs' traffic in tenant %s reach Ext-Rtr " %(tnt1))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-12: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt1))

    #Step 13:
    if test_traff.traff_from_extrtr_to_fips('ml2',tnt1) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-13: EXT-RTR can reach the FIPs of tenant %s " %(tnt1))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-13: EXT-RTR can reach the FIPs of tenant %s : PASS" %(tnt1))
	
    LOG.info(
    "###### WORKFLOW-2: Attaching router to networks AFTER VM creation:Tenant %s ######" 
    %(tnt2))

    #Step 14:
    if test_conf.install_tenant_vms(tnt2) == 0:
    	raise TestError("ML2-SANITY: Test-14: Create VMs for tenant %s " %(tnt2))
    
    else:
    	LOG.info("ML2-SANITY: Test-14: Create VMs for tenant %s : PASS" %(tnt2))

    sleep(15) #For VMs to get learned in Fabric

    #Step 15:
    if test_traff.traff_from_ml2_tenants(tnt2) == 1:
    	LOG.error(
    	"ML2-SANITY: Test-15: VMs b/w Networks/EPGs must NOT be reachable for tenant %s " %(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-15: VMs in different Networks/EPGs have DHCP addresses in tenant %s : PASS" %(tnt2))
    	LOG.info(
    	"ML2-SANITY: Test-15: VMs are reachable(ICMP & SSH) from netns(DHCP-server) for tenant %s : PASS" %(tnt2))
    	LOG.info(
    	"ML2-SANITY: Test-15: VMs b/w Networks/EPGs must NOT be reachable for tenant %s : PASS" %(tnt2))
    	LOG.info(
    	"ML2-SANITY: Test-15: MetaData for VMs in tenant %s : PASS" %(tnt2))
        LOG.info(
        "ML2-SANITY: Test-15: Intra-subnet/intra-BD traffic between VMs in tenant %s : PASS" %(tnt2))

    #Step 16:
    if test_conf.attach_routers_to_networks(tnt2) == 0:
    	raise TestError(
    	"ML2-SANITY: Test-16: Attach Routers to two networks in tenant %s "
     	%(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-16: Attach Routers to two networks in tenant %s : PASS"
     	%(tnt2))

    sleep(10) #Almost immediate, so sleep

    #Step 17:
    if test_traff.traff_from_ml2_tenants(tnt2,proto=['icmp','tcp']) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-17: VMs b/w Networks/EPGs are NOT reachable in tenant %s " %(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-17: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : PASS" %(tnt2))

    #Step 18:
    if test_conf.attach_router_to_extnw(tnt2) == 0:
    	raise TestError(
    	"ML2-SANITY: Test-18: Attach router of tenant %s connects to shared External Ntk " %(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-18: Attach router of tenant %s connects to shared External Ntk : PASS" %(tnt2))

    sleep(5) #Almost immediate was cause traff failure below, hence sleep
    #Step 19:
    if test_traff.traff_from_ml2_tenants(tnt2,ext=True,proto=['icmp','tcp']) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-19: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr " %(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-19: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt2))

    #Step 20:
    if attach_fip_to_vms(tnt2,'ml2') == 0:
    	raise TestError(
    	"ML2-SANITY: Test-20: Attach FIP to VMs in tenant %s " %(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-20: Attach FIP to VMs in tenant %s : PASS" %(tnt2))

    sleep(10) #FIP to get learned at Fabric

    #Step 21:
    if test_traff.traff_from_ml2_tenants(tnt2,ext=True,proto=['icmp','tcp']) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-21: Using FIP VMs' traffic in tenant %s reach Ext-Rtr " %(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-21: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt2))

    #Step 22:
    if test_traff.traff_from_extrtr_to_fips('ml2',tnt2) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-22: EXT-RTR can reach the FIPs of tenant %s " %(tnt2))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-22: EXT-RTR can reach the FIPs of tenant %s : PASS" %(tnt2))
except TestError as e:
    LOG.error("%s : FAIL" %(e))
finally:
    LOG.info("Cleanup being called finally")
    test_conf.cleanup_ml2()
    LOG.info("THE EXECUTION OF ML2 SANITY TESTRUN COMPLETES")
    

