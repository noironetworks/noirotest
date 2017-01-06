from test_sanity import *
LOG.setLevel(logging.INFO)
tnt1 = TNT_LIST_GBP
LOG.info("#### Start of GBP Sanity for the Tenant == %s #####"
         %(tnt1))
#Initialize the GBP CRUD Class
test_conf = crudGBP()

LOG.info("Create Openstack Tenants for GBP ")
test_conf.create_gbp_tenants()

### Every Step is a Test by itself, so it will log as Test instead of Step ###

try:
    #Step 1:
    if test_conf.create_l2p() == 0:
        raise TestError("GBP-SANITY: Test-1: Create L2Policies, AutoPTGs, Implicit L3Policies")
    else:
        LOG.info("GBP-SANITY: Test-1: Create L2Policies, AutoPTGs, Implicit L3Policies : PASS")

    #Step 2:
    if test_conf.create_ptg() == 0:
        raise TestError("GBP-SANITY: Test-2: Create Regular PTG using existing L2P")
    else:
        LOG.info("GBP-SANITY: Test-2: Create Regular PTG using existing L2P : PASS")

    #Step 3:
    if test_conf.create_policy_target() == 0:
        raise TestError(
        "GBP-SANITY: Test-3: Create Policy-Targets on Regular & AutoPTGs")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-3: Create Policy-Targets on Regular & AutoPTGs : PASS")

    #Step 4: 
    if test_conf.create_contracts() == 0:
        raise TestError("GBP-SANITY: Test-4: Create Shared Contracts & Relational resources")
    else:
        LOG.info("GBP-SANITY: Test-4: Create Shared Contracts & Relational resources : PASS")

    #Step 5:
    if test_conf.install_tenant_vms() == 0:
        raise TestError(
        "GBP-SANITY: Test-5: Spawning VMs off the Regular and AutoPTGs")
    else:
        LOG.info(
        "GBP-SANITY: Test-5: Spawning VMs off the Regular and AutoPTGs : PASS")
    
    #Initialize Traffic Class
    test_traff = sendTraffic()

    #Step 6:
    if test_traff.traff_from_gbp_tenant(tnt1,'intra_epg') == 0:
    	raise TestError(
    	"GBP-SANITY: Test-6: INTRA-EPG traffic between VMs in an AutoPTG %s"
     	%(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-6: INTRA-EPG traffic between VMs in an AutoPTG %s : PASS"
     	%(tnt1))
    sys.exit(1) #JISHNU 
    #Step 7: 
    if test_conf. == 0:
    	raise TestError(
    	"GBP-SANITY: Test-7: Attach router of tenant %s connects to shared External Ntk "
     	%(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-7: Attach router of tenant %s connects to shared External Ntk : PASS"
    	%(tnt1))

    #Step 8:
    if test_conf.install_tenant_vms(tnt1) == 0:
    	raise TestError("GBP-SANITY: Test-8: Create VMs for tenant %s " %(tnt1))
    else:
    	LOG.info("GBP-SANITY: Test-8: Create VMs for tenant %s : PASS" %(tnt1))

    sleep(15)
    #Initialize the Traffic Class
    test_traff = sendTraffic()

    #Step 9:
    if test_traff.traff_from_ml2_tenants(tnt1) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-9: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s " %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-9: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : PASS" %(tnt1))
    	LOG.info(
    	"GBP-SANITY: Test-9: VMs in different Networks/EPGs have DHCP addresses in tenant %s : PASS" %(tnt1))
    	LOG.info(
    	"GBP-SANITY: Test-9: VMs are reachable(ICMP & SSH) from netns(DHCP-server) for tenant %s : PASS" %(tnt1))

    #Step 10:
    if test_traff.traff_from_ml2_tenants(tnt1,ext=True) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-10: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr " %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-10: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt1))

    #Step 11:
    if test_conf.attach_fip_to_vms(tnt1) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-11: Attach FIP to VMs in tenant %s " %(tnt1))
    else:
   	LOG.info(
    	"GBP-SANITY: Test-11: Attach FIP to VMs in tenant %s : PASS" %(tnt1))
    sleep(20) #For FIP to be learned in Fabric
    #Step 12:
    if test_traff.traff_from_ml2_tenants(tnt1,ext=True) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-12: Using FIP VMs' traffic in tenant %s reach Ext-Rtr " %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-12: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt1))

    LOG.info(
    "###### WORKFLOW-2: Attaching router to networks AFTER VM creation:Tenant %s ######" 
    %(tnt2))
    #Step 13:
    if test_conf.install_tenant_vms(tnt2) == 0:
    	raise TestError("GBP-SANITY: Test-13: Create VMs for tenant %s " %(tnt2))
    
    else:
    	LOG.info("GBP-SANITY: Test-13: Create VMs for tenant %s : PASS" %(tnt2))

    sleep(15) #For VMs to get learned in Fabric

    #Step 14:
    if test_traff.traff_from_ml2_tenants(tnt2) == 1:
    	raise TestError(
    	"GBP-SANITY: Test-14: VMs b/w Networks/EPGs must NOT be reachable for tenant %s " %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-14: VMs in different Networks/EPGs have DHCP addresses in tenant %s : PASS" %(tnt2))
    	LOG.info(
    	"GBP-SANITY: Test-14: VMs are reachable(ICMP & SSH) from netns(DHCP-server) for tenant %s : PASS" %(tnt2))
    	LOG.info(
    	"GBP-SANITY: Test-14: VMs b/w Networks/EPGs must NOT be reachable for tenant %s : PASS" %(tnt2))

    #Step 15:
    if test_conf.attach_routers_to_networks(tnt2) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-15: Attach Routers to two networks in tenant %s "
     	%(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-15: Attach Routers to two networks in tenant %s : PASS"
     	%(tnt2))

    #Step 16:
    if test_traff.traff_from_ml2_tenants(tnt2) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-16: VMs b/w Networks/EPGs are NOT reachable in tenant %s " %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-16: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : PASS" %(tnt2))

    #Step 17:
    if test_conf.attach_router_to_extnw(tnt2) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-17: Attach router of tenant %s connects to shared External Ntk " %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-17: Attach router of tenant %s connects to shared External Ntk : PASS" %(tnt2))

    #Step 18:
    if test_traff.traff_from_ml2_tenants(tnt2,ext=True) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-18: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr " %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-18: Using SNAT VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt2))

    #Step 19:
    if test_conf.attach_fip_to_vms(tnt2) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-19: Attach FIP to VMs in tenant %s " %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-19: Attach FIP to VMs in tenant %s : PASS" %(tnt2))

    sleep(20) #FIP to get learned at Fabric

    #Step 20:
    if test_traff.traff_from_ml2_tenants(tnt1,ext=True) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-20: Using FIP VMs' traffic in tenant %s reach Ext-Rtr " %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-20: Using FIP VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt2))
except TestError as e:
    raise TestError("%s : FAIL" %(e))
    test_conf.cleanup_ml2()
finally:
    LOG.info("THE EXECUTION OF ML2 SANITY TESTRUN COMPLETES, cleanup starts")
    test_conf.cleanup_ml2()
    

