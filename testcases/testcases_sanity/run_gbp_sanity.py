from test_sanity import *
from commands import *
tnt1,tnt2 = TNT_LIST_GBP
LOG.info("#### Start of GBP SANITY #####")
#Initialize the GBP CRUD Class
test_conf = crudGBP()
#Initialize Traffic Class
test_traff = sendTraffic()
LOG.info("Create Openstack Tenants for GBP ")
test_conf.create_gbp_tenants()

### Every Step is a Test by itself, so it will log as Test instead of Step ###

try:
    #Step 1:
    if test_conf.create_l2p_l3p(tnt1) == 0:
        raise TestError("GBP-SANITY: Test-1: Create L2Policies, AutoPTGs, Implicit L3Policies")
    else:
        LOG.info("GBP-SANITY: Test-1: Create L2Policies, AutoPTGs, Implicit L3Policies : PASS")

    #Step 2:
    if test_conf.create_ptg() == 0:
        raise TestError("GBP-SANITY: Test-2: Create Regular PTG using existing L2P")
    else:
        LOG.info("GBP-SANITY: Test-2: Create Regular PTG using existing L2P : PASS")

    #Step 3:
    if test_conf.create_policy_target(tnt1) == 0:
        raise TestError(
        "GBP-SANITY: Test-3: Create Policy-Targets on Regular & AutoPTGs")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-3: Create Policy-Targets on Regular & AutoPTGs : PASS")

    #Step 4: 
    if test_conf.create_shared_contracts() == 0:
        raise TestError("GBP-SANITY: Test-4: Create Shared Contracts & Relational resources")
    else:
        LOG.info("GBP-SANITY: Test-4: Create Shared Contracts & Relational resources : PASS")

    #Step 5:
    if test_conf.install_tenant_vms(tnt1) == 0:
        raise TestError(
        "GBP-SANITY: Test-5: Spawning VMs off the Regular and AutoPTGs")
    else:
        LOG.info(
        "GBP-SANITY: Test-5: Spawning VMs off the Regular and AutoPTGs : PASS")
    
    #Step 6:
    if test_traff.traff_from_gbp_tenant(tnt1,'intra_epg') == 0:
    	LOG.error(
    	"GBP-SANITY: Test-6: INTRA-EPG traffic between VMs in an AutoPTG %s"
     	%(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-6: INTRA-EPG traffic between VMs in an AutoPTG %s : PASS"
     	%(tnt1))
	LOG.info(
    	"GBP-SANITY: Test-6: VMs b/w Networks/EPGs are reachable(ICMP & SSH) in tenant %s : PASS" %(tnt1))
    	LOG.info(
    	"GBP-SANITY: Test-6: VMs in different Networks/EPGs have DHCP addresses in tenant %s : PASS" %(tnt1))
    	LOG.info(
    	"GBP-SANITY: Test-6: VMs are reachable(ICMP & SSH) from netns(DHCP-server) for tenant %s : PASS" %(tnt1))

    #Step 7: 
    if test_conf.update_intra_bd_ptg_by_contract(PRS_ICMP_TCP) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-7: Apply Contract %s between intra-BD EPGs by updation"
     	%(PRS_ICMP_TCP))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-7: Apply Contract %s between intra-BD EPGs by updation : PASS"
    	%(PRS_ICMP_TCP))

    #Step 8:
    if test_traff.traff_from_gbp_tenant(tnt1,'intra_bd') == 0:
    	LOG.error(
    	"GBP-SANITY: Test-8: INTRA-BD traffic between VMs across two EPGs")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-8: INTRA-BD traffic between VMs across two EPGs : PASS")

    #Step 9:
    if test_conf.update_inter_bd_ptg_by_contract(PRS_ICMP_TCP) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-9: Apply Contract %s between inter-BD EPGs by updation"
     	%(PRS_ICMP_TCP))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-9: Apply Contract %s between inter-BD EPGs by updation : PASS"
    	%(PRS_ICMP_TCP))

    #Step 10
    if test_traff.traff_from_gbp_tenant(tnt1,'inter_bd') == 0:
    	LOG.error(
    	"GBP-SANITY: Test-10: INTER-BD traffic between VMs across three EPGs")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-10: INTER-BD traffic between VMs across three EPGs : PASS")

    #Step 11	
    if test_conf.create_ext_seg('nat') == 0:
    	raise TestError(
    	"GBP-SANITY: Test-11: Create of shared External-Segment in Tenant-Admin")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-11: Create of shared External-Segment in Tenant-Admin : PASS")
	
    #Step 12
    if test_conf.create_ext_pol(tnt1) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-12: Create of External Policy in tenant %s" %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-12: Create of External Policy in tenant %s : PASS" %(tnt1))

    #Step 13
    if test_conf.attach_l3p_extseg(tnt1) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-13: Updating L3Policy to attach to External Segment in tenant %s"
        %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-13: Updating L3Policy to attach to External Segment in tenant %s : PASS"
        %(tnt1))

    #Step 14
    if test_conf.update_allptgs_by_contract_for_extraff(PRS_ICMP_TCP) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-14: Apply ICMP&TCP contract to all Private & External EPGs in tenant %s"
        %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-14: Apply ICMP&TCP contract to all Private & External EPGs in tenant %s : PASS"
        %(tnt1))

    sleep(5)
    #Step 15
    if test_traff.traff_from_gbp_tenant(tnt1,'intra_epg',ext=True) == 0:
    	LOG.error(
    	"GBP-SANITY: Test-15: SNAT Traffic from %s VMs to External Router" %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-15: SNAT Traffic from %s VMs to External Router : PASS" %(tnt1))

    #Step 16
    if attach_fip_to_vms(tnt1,'gbp') == 0:
    	raise TestError(
    	"GBP-SANITY: Test-16: Associate dynamically FIPs to VMs External Router in tenant %s"
        %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-16: Associate dynamically FIPs to VMs External Router in tenant %s: PASS"
	%(tnt1))
	
    #Step 17
    if test_traff.traff_from_extrtr_to_fips('gbp',tnt1) == 0:
    	LOG.error(
    	"GBP-SANITY: Test-17: Send traffic from External Router to VMs in tenant %s"
        %(tnt1))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-17: Send traffic from External Router to VMs in tenant %s: PASS"
	%(tnt1))

    ############# BELOW IS THE WORKFLOW for GBP NO-NAT ###################
    #Step 18:
    if test_conf.create_l2p_l3p(tnt2) == 0:
        raise TestError("GBP-SANITY: Test-18: Create AddressScope, Explicit L3Policy & L2Policy")
    else:
        LOG.info("GBP-SANITY: Test-18: Create AddressScope, Explicit L3Policy & L2Policy : PASS")

    #Step 19:
    if test_conf.create_policy_target(tnt2) == 0:
        raise TestError(
        "GBP-SANITY: Test-19: Create Policy-Targets on AutoPTGs")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-19: Create Policy-Targets on AutoPTGs : PASS")

    #Step 20:
    if test_conf.install_tenant_vms(tnt2) == 0:
        raise TestError(
        "GBP-SANITY: Test-20: Spawning VMs off the AutoPTG")
    else:
        LOG.info(
        "GBP-SANITY: Test-20: Spawning VMs off the AutoPTG : PASS")

    #Step 21	
    if test_conf.create_ext_seg('nonat') == 0:
    	raise TestError(
    	"GBP-SANITY: Test-21: Create of shared External-Segment for NoNAT in Tenant-Admin")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-21: Create of shared External-Segment for NoNAT in Tenant-Admin : PASS")
	
    #Step 22
    if test_conf.create_ext_pol(tnt2) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-22: Create of External Policy for NoNAT in tenant %s" %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-22: Create of External Policy for NoNAT in tenant %s : PASS" %(tnt2))

    #Step 23
    if test_conf.attach_l3p_extseg(tnt2) == 0:
    	raise TestError(
    	"GBP-SANITY: Test-23: Updating L3Policy to attach to NoNAT External Segment in tenant %s"
        %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-23: Updating L3Policy to attach to NoNAT External Segment in tenant %s : PASS"
        %(tnt2))

    #Step 24
    if test_conf.update_ptg_extptg_nonat_traff(PRS_ICMP_TCP):
    	raise TestError(
    	"GBP-SANITY: Test-24: Apply contract onf ExtPol & AutoPtg got NoNAT")
    else:
    	LOG.info(
    	"GBP-SANITY: Test-24: Apply contract onf ExtPol & AutoPtg got NoNAT : PASS")

    #Step 25
    if test_traff.traff_from_gbp_tenant(tnt2,'intra_epg',ext=True) == 0:
    	LOG.error(
    	"GBP-SANITY: Test-25: NoNAT Traffic from %s VMs to External Router" %(tnt2))
    else:
    	LOG.info(
    	"GBP-SANITY: Test-25: NoNAT Traffic from %s VMs to External Router : PASS" %(tnt2))
except TestError as e:
    LOG.error("%s : FAIL" %(e))
finally:
    LOG.info("Cleanup being called finally")
    test_conf.cleanup_gbp()
    LOG.info("THE EXECUTION OF GBP SANITY TESTRUN COMPLETES")
    dump_results('GBP')
    

