from common_sanity_methods import *
from commands import *
tnt1,tnt2,tnt3 = TNT_LIST_ML2
LOG.info("#### Start of ML2 Sanity #####")

#Initialize the ML2 CRUD Class
test_conf = crudML2()
#Initialize the Traffic Class
test_traff = sendTraffic()
LOG.info("#### Create Openstack Tenants for ML2 ####")
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
    if test_traff.traff_from_ml2_tenants(tnt2, no_ipv6=True) == 1:
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

    if conf.get('dual_stack') and conf['dual_stack'] == True:
        if test_conf.reboot_vms(tnt2) == 0:
           raise TestError(
           "ML2-SANITY: Test-16.5: Rebooting VMs in tenant %s "
           %(tnt2))
        else:
           LOG.info(
           "ML2-SANITY: Test-16.5: Rebooting in tenant %s : PASS"
           %(tnt2))
        sleep(15)

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
    
    # NO-NAT Test
    LOG.info(
    "####### WORKFLOW-3: NO-NAT with Shared Address-Scope and Tenant-specific subnetpool %s ######" 
    %(tnt3))

    #Step 23:
    if test_conf.create_add_scope('admin',shared=True,vrf=True) == 0:
        raise TestError("ML2-SANITY: Test-23: Create Shared Address-Scope for NoNAT"\
		        "in tenant Admin")
    else:
        LOG.info("ML2-SANITY: Test-23: Create Shared Address-Scope for NoNAT"\
		 " in tenant Admin: PASS")

    #Step 24:
    if test_conf.create_subnetpool(tnt3,shared=True) == 0:
        raise TestError("ML2-SANITY: Test-24: Create tenant %s SubnetPool using"\
		       " Shared Address-Scope" %(tnt3))
    else:
        LOG.info("ML2-SANITY: Test-24: Create tenant %s SubnetPool using"\
		 " Shared Address-Scope: PASS" %(tnt3))

    #Step 25:
    if test_conf.create_pvt_network_subnets(nonat=True) == 0:
    	raise TestError(
    	"ML2-SANITY: Test-25: Create private network for NO-NAT tenant %s " %(tnt3))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-25: Create private network for NO-NAT tenant %s : PASS" %(tnt3))

    #Step 26:
    if test_conf.install_tenant_vms(tnt3) == 0:
    	raise TestError("ML2-SANITY: Test-26: Create VMs for tenant %s " %(tnt3))
    else:
    	LOG.info("ML2-SANITY: Test-26: Create VMs for tenant %s : PASS" %(tnt3))

    #Step 27:
    if test_conf.attach_routers_to_networks(tnt3) == 0:
    	raise TestError(
    	"ML2-SANITY: Test-27: Attach Routers to two networks in tenant %s"\
	" using shared address-scope of tenant admin"
     	%(tnt3))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-27: Attach Routers to two networks in tenant %s"\
	" using shared address-scope of tenant admin"
     	%(tnt3))

    #Step 28
    if create_external_network_subnets('nonat') == 0:
        raise TestError(
        "ML2-SANITY: Test-28: Create shared External Ntk in Admin-tenant for NoNAT ")
    else:
        LOG.info(
        "ML2-SANITY: Test-28: Create shared External Ntk in Admin-tenant for NoNAT : PASS")

    #Step 29:
    if test_conf.attach_router_to_extnw(tnt3,nonat=True) == 0:
    	raise TestError(
    	"ML2-SANITY: Test-29: Attach router of tenant %s connects to shared External Ntk" %(tnt3))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-29: Attach router of tenant %s connects to shared External Ntk : PASS" %(tnt3))

    sleep(5)
    if conf.get('dual_stack') and conf['dual_stack'] == True:
        if test_conf.reboot_vms(tnt3) == 0:
           raise TestError(
           "ML2-SANITY: Test-29.5: Rebooting VMs in tenant %s "
           %(tnt2))
        else:
           LOG.info(
           "ML2-SANITY: Test-29.5: Rebooting in tenant %s : PASS"
           %(tnt2))
        sleep(20)

    #Step 30:
    if test_traff.traff_from_ml2_tenants(tnt3,ext=True,proto=['icmp','tcp']) == 0:
    	LOG.error(
    	"ML2-SANITY: Test-30: Using NoNAT VMs' traffic in tenant %s reach Ext-Rtr: FAIL" %(tnt3))
    else:
    	LOG.info(
    	"ML2-SANITY: Test-30: Using NoNAT VMs' traffic in tenant %s reach Ext-Rtr : PASS" %(tnt3))

except TestError as e:
    LOG.error("%s : FAIL" %(e))
finally:
    LOG.info("Cleanup being called finally")
    test_conf.cleanup_ml2()
    LOG.info("THE EXECUTION OF ML2 SANITY TESTRUN COMPLETES")
    dump_results('ML2')
    

