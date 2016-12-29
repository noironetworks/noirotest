#!/usr/bin/python

import datetime
import logging
import sys

from time import sleep
from libs.gbp_aci_libs import gbpApic
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_nova_libs import gbpNova
from libs.raise_exceptions import *
from libs.gbp_utils import *
from traff_from_extgw import *
from traff_from_allvms_to_extgw import NatTraffic


class NatFuncTestMethods(object):
    """
    This is a GBP NAT Functionality TestCase
    """
    # NOTE: In this code structure, we have mostly re-used the same
    # local variable, as on every instance/invoke of the method new
    # value will be associated to the local variable within the
    # function scope

    # Initialize logging
    _log = logging.getLogger()
    hdlr = logging.FileHandler('/tmp/natfunctestsuite.log')
    #formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    formatter = logging.Formatter('%(asctime)s %(message)s')
    hdlr.setFormatter(formatter)
    _log.addHandler(hdlr)
    _log.setLevel(logging.INFO)

    def __init__(self,cntlrip,ntknode):
        self.cntlrip = cntlrip
        self.gbpcrud = GBPCrud(cntlrip)
        self.gbpnova = gbpNova(cntlrip)
        self.extsegname = 'Management-Out'
        self.natpoolname1 = 'GbpNatPoolTest1'
        self.natpoolname2 = 'GbpNatPoolTest2'
        self.natippool1 = '55.55.55.0/24'
        self.natippool2 = '66.66.66.0/24'
        self.snatpool = '50.50.50.0/24'
        self.snatcidr = '50.50.50.1/24'
        self.l3pname = 'L3PNat'
        self.l3pippool = '20.20.20.0/24'
        self.l3ppreflen = 26
        self.l2pname = 'L2PNat'
        self.ptg1name = 'TestPtg1'
        self.ptg2name = 'TestPtg2'
        self.MgmtOutExtPol = 'MgmtExtPol'
        self.DcOutExtPol = 'DcExtPol'
        self.vm1name = 'TestVM1'
        self.vm2name = 'TestVM2'
        self.vmlist = [self.vm1name, self.vm2name]
        self.nat_traffic = NatTraffic(
            cntlrip, self.vmlist, ntknode)
     
    def addhostpoolcidr(self,fileloc='/etc/neutron/neutron.conf',
                        l3out='Management-Out',delete=False,
                        restart=True,flag=''):
        """
        Add host_pool_cidr config flag and restarts neutron-server
        fileloc :: location of the neutron config
                   file in which apic_external_network
                   section is defined
        """
        patternchk = 'host_pool_cidr'
        pattern = 'host_pool_cidr=%s' %(self.snatcidr)
        section = 'apic_external_network:%s' %(l3out)
        if not delete:
            if flag == 'default_external_segment_name':
               self._log.info(
               "\nAdding default_external_segment_name to neutron conf")
               pat='default_external_segment_name=Management-Out'
               sect='group_policy_implicit_policy'
               editneutronconf(self.cntlrip,
                            fileloc,
                            pat,
                            section=sect
                           )
            else:
                self._log.info("\nAdding host_pool_cidr to neutron conf")
                editneutronconf(self.cntlrip,
                            fileloc,
                            pattern,
                            section=section
                           )
        if delete:
            self._log.info(
            "\nDeleting if any, host_pool_cidr & def_ext_seg_name"
            "from neutron conf")
            if not flag:
                editneutronconf(self.cntlrip,
                            fileloc,
                            'default_external_segment_name',
                            add=False,
                            restart=False
                           )
            editneutronconf(self.cntlrip,
                            fileloc,
                            patternchk,
                            add=False) 

    def testCreateExtSegWithDefault(self,extsegname):
        """
        Create External Segment
        """
        self._log.info(
        "\nStep: Create External Segment %s\n" %(extsegname))
        self.extsegid = self.gbpcrud.create_gbp_external_segment(
                                       extsegname,
                                       external_routes = [{
                                           'destination':'0.0.0.0/0',
                                           'nexthop': None}]
                                       )
        if self.extsegid == 0:
            self._log.error(
            "\n///// Step: External Segment Creation %s failed /////"
            %(extsegname))
            return 0
        else:
            return self.extsegid

    def testCreateNatPoolAssociateExtSeg(self,poolname='',natpool='',extsegid=''):
        """
        Create a NAT pool and associate the existing External Segment
        """
        self._log.info(
        "\nStep: Create a NAT pool and associate the existing External Segment\n")
        if natpool == '':
           natpool = self.natippool1
        if poolname == '':
           poolname = self.natpoolname1
        if extsegid == '':
           extsegid = self.extsegid
        self.nat_pool_id = self.gbpcrud.create_gbp_nat_pool(
                                        poolname,
                                        ip_pool = natpool,
                                        external_segment_id = extsegid)
        if self.nat_pool_id == 0:
            self._log.error(
                "\n///// Create the NAT pool with reference to"
                  " the existing External Segment failed /////")
            return 0
	return 1

    def testUpdateNatPoolAssociateExtSeg(self,extsegid):
        """
        Update External Segment in a NAT Pool
        """
        # Since self.nat_pool_id is the ONLY natpool in the system hence making it
        # the default value
        self._log.info(
            "\nStep: Update a NAT pool and associate the existing External Segment\n")
        if self.gbpcrud.update_gbp_nat_pool(
                                        self.nat_pool_id,
                                        external_segment_id = extsegid
                                        ) == 0:
           self._log.error(
                "\n///// Update External Segment in" 
                " existing NAT pool failed /////")
           return 0
	return 1

    def testCreatePtgDefaultL3p(self):
        """
        Step to Create Policy Target group with Default L3
        Fetch the UUID of the 'default' L3Policy
        """
        self._log.info(
                  "\nStep: Create Policy Target group with Default L3\n")
        self.ptg1id = self.gbpcrud.create_gbp_policy_target_group(
                                     self.ptg1name)
        if self.ptg1id == 0:
            self._log.error(
            "\n///// Create Policy Target group with Default L3 failed /////")
                
            return 0
        self.defaultl3pid = self.gbpcrud.verify_gbp_l3policy('default') 
        if self.defaultl3pid == 0:
           self._log.error("\n///// Failed to fetch UUID of Default L3P /////")
           return 0
	return 1

    def testCreateNonDefaultL3pAndL2p(self):
        """
        Step to Create Non-default L3P
        """
        self._log.info("\nStep: Create non-default L3Policy and L2Policy\n")
        self.nondefaultl3pid = self.gbpcrud.create_gbp_l3policy(
                                               self.l3pname,
                                               ip_pool=self.l3pippool,
                                               subnet_prefix_length=self.l3ppreflen)
        if self.nondefaultl3pid == 0:
            self._log.error(
            "\n///// Creation of non-default L3Policy failed /////")
            
            return 0
        self.l2policy_id = self.gbpcrud.create_gbp_l2policy(
                                self.l2pname,
                                l3_policy_id=self.nondefaultl3pid)
        if self.l2policy_id == 0:
            self._log.error(
            "\n///// Creation of non-default L2Policy failed /////")
            return 0
	return 1

    def testCreatePtgWithNonDefaultL3p(self):
        """
        Step to Create Policy Target group with Created L3
        """
        self._log.info("\nStep: Create Policy Target group with Created L3\n")
        self.ptg2id = self.gbpcrud.create_gbp_policy_target_group(
                                     self.ptg2name,
                                     l2_policy_id=self.l2policy_id)
        if self.ptg2id == 0:
            self._log.error(
            "\n////// Create Policy Target group "
            "with non-default L3Policy failed /////")
            return 0
	return 1

    def testAssociateExtSegToBothL3ps(self,extsegid='',both=True,l3ptype=''):
        """
        Step to Associate External Segment to 
        both default & non-default L3Ps
        both: True/False, defaulted to use both L3Ps
              else(False) user should pass the l3ptype
        l3ptype: valid strings are 'default' or 'nondefault'
        """
        if extsegid == '':
           extsegid = self.extsegid
        if both:
            self._log.info(
                     "\nStep: Associate External Segment to both L3Ps\n")
            for l3p in [self.defaultl3pid,self.nondefaultl3pid]:
                if self.gbpcrud.update_gbp_l3policy(l3p,
                                                property_type='uuid',
                                                external_segments=extsegid
                                                ) == 0:
                    self._log.error(
                    "\n///// Associate External Segment to L3P failed /////")
                    return 0
        else:
            if l3ptype == 'default':
                l3p = self.defaultl3pid
            else:
                l3p = self.nondefaultl3pid
            self._log.info("\nStep:Associate External Segment to Single L3P")
            if self.gbpcrud.update_gbp_l3policy(l3p,
                                                property_type='uuid',
                                                external_segments=extsegid
                                                ) == 0:
               self._log.error(
               "\n///// Associate External Segment to Single L3P failed /////")
               return 0 
	return 1
        
    def testCreatePolicyTargetForEachPtg(self):
        """
        Created Port Targets
        """
        self._log.info(
                 "\nStep: Create Policy Targets for each of the two PTGs \n")
        self.pt1id = self.gbpcrud.create_gbp_policy_target('pt1', self.ptg1name, 1)
        if self.pt1id == 0:
            self._log.error(
            "\n///// Creation of Policy Targe failed for PTG=%s /////"
            %(self.ptg1name))
            
            return 0
        self.pt2id = self.gbpcrud.create_gbp_policy_target('pt2', self.ptg2name, 1)
        if self.pt2id == 0:
            self._log.error(
            "\n///// Creation of Policy Targe failed for PTG=%s /////"
            %(self.ptg2name))
            return 0
	return 1

    def testCreateUpdateExternalPolicy(self,update=0,delete=0,
                                       extseg='',extpol='default'):
        """
        Create ExtPolicy with ExtSegment
        Apply Policy RuleSets
        update:: 1, then MUST pass extseg(the new extsegid to which
                    this existing ExtPol should now associate to
        """
        if extpol == 'default':
           self.extpolname = self.MgmtOutExtPol
        else:
           self.extpolname = self.DcOutExtPol
        if delete == 1:
            self._log.info("\nStep: Delete ExtPolicy")  
            if self.gbpcrud.delete_gbp_external_policy(
                           self.extpolid
                           ) == 0:
               self._log.error(
                    "\n///// Deletion of External Policy failed /////")   
               return 0
        elif update == 1:
            self._log.info(
            "\nStep: Update ExtPolicy with External Segment")  
            if self.gbpcrud.update_gbp_external_policy(
                           self.extpolname,
                           external_segments=[extseg]
                           ) == 0:
               self._log.error(
               "\n///// Updation of External Policy with ExtSeg failed /////")   
               return 0
        else:
           self._log.info(
           "\nStep: Create ExtPolicy with ExtSegment and Apply PolicyRuleSets\n")
           if extseg == '':
              extseg = self.extsegid    
           self.extpolid = self.gbpcrud.create_gbp_external_policy(
                             self.extpolname,
                             external_segments=[extseg]
                                                              )
           if self.extpolid == 0:
              self._log.error(
              "\n ///// Creation of External Policy failed /////")
              return 0
           return self.extpolid
	return 1
   
    def testVerifyCfgdObjects(self,nat_type='dnat'):
        """
        Verify all the configured objects and their atts
        """
        self._log.info(
                 "\nStep: Verify the Configured Objects and their Attributes\n")
        if self.gbpcrud.verify_gbp_any_object('l3_policy',
                                               self.nondefaultl3pid,
                                               external_segments = self.extsegid,
                                               l2_policies = self.l2policy_id,
                                               ip_pool = self.l3pippool
                                              ) == 0:  
           self._log.error("\n///// Verify for L3Policy Failed /////")
           return 0
        if self.gbpcrud.verify_gbp_any_object('l2_policy',
                                               self.l2policy_id,
                                               l3_policy_id = self.nondefaultl3pid,
                                               policy_target_groups = self.ptg2id
                                              ) == 0:
           self._log.error("\n///// Verify for L2Policy Failed /////")
           return 0
        if nat_type == 'dnat':
            if self.gbpcrud.verify_gbp_any_object('external_segment',
                                               self.extsegid,
                                               l3_policies = [self.defaultl3pid,
                                                              self.nondefaultl3pid],
                                               nat_pools = self.nat_pool_id,
                                               external_policies = self.extpolid
                                              ) == 0:
                self._log.error("\n///// Verify for DNAT ExtSeg Failed /////")
                return 0
        else:
            if self.gbpcrud.verify_gbp_any_object('external_segment',
                                               self.extsegid,
                                               l3_policies = [self.defaultl3pid,
                                                              self.nondefaultl3pid],
                                               external_policies = self.extpolid
                                              ) == 0:
               
                self._log.error("\n///// Verify for SNAT ExtSeg Failed /////")
                return 0
	return 1

    def testLaunchVmsForEachPt(self,az2='',same=False):
        """
        Launch VMs in two diff avail-zones
        az2:: second avail-zone, az1=nova(default)
        same:: True, then VMs launched in same avail-zone
        """
        az1 = 'nova' #default in openstack
        if same:
           az2 = az1
           self._log.info("\nStep: Launch VMs in same avail-zones\n")
        else:
            self._log.info("\nStep: Launch VMs in two diff avail-zones\n")
        # launch Nova VMs
        if self.gbpnova.vm_create_api(self.vm1name,
                                      'ubuntu_multi_nics',
                                      self.pt1id[1],
                                      avail_zone=az1) == 0:
           self._log.error(
           "\n///// VM Create using PTG %s failed /////" %(self.ptg1name))
           return 0
        if self.gbpnova.vm_create_api(self.vm2name,
                                      'ubuntu_multi_nics',
                                      self.pt2id[1],
                                      avail_zone=az2) == 0:
           self._log.error(
           "\n///// VM Create using PTG %s failed /////" %(self.ptg2name))
           return 0
	return 1

    def testAssociateFipToVMs(self,ExtSegName='Management-Out',ic=False):
        """
        Associate FIPs to VMs
        ic:: True, means FIP already exists, user needs
                to statically interchange the FIP among the VMs
        """
        VMs = [self.vm1name,self.vm2name]
        if not ic:
            self._log.info("\nStep: Dynamically Associate FIPs to VMs\n")
            self.vm_to_fip = {}
            for vm in VMs:
                results = self.gbpnova.action_fip_to_vm(
                                          'associate',
                                          vm,
                                          extsegname=ExtSegName
                                          )
                if not results:
                   self._log.error(
                   "\n///// Dynamic Association FIP to VM %s failed /////" %(vm))
                   #if the above function is called for a negative check
                   #then it may or may not have already created the FIPs
                   #So ensure to delete those FIPs(apparently this we were
                   #not doing so TC-4 was failing at Step=Negative Check
                   self.gbpnova.delete_release_fips()
                   return 0
                else:
                   self.vm_to_fip[vm] = results[0]
        if ic:
            self._log.info(
            "\nStep: Statically Inter-Changing Association of FIPs to VMs\n")
            if self.gbpnova.action_fip_to_vm(
                                            'associate',
                                            VMs[0],
                                            vmfip=self.vm_to_fip[VMs[1]]
                                            ) and \
               self.gbpnova.action_fip_to_vm(
                                            'associate',
                                            VMs[1],
                                            vmfip=self.vm_to_fip[VMs[0]]
                                            ):
               print "Success in Static Assignment of FIP to VMs"
            else:
               self._log.error(
               "\n///// Static Association of FIP to VM %s failed /////")
               return 0
	return 1

    def testDisassociateFipFromVMs(self,release_fip=True,vmname=False):
        """
        Disassociate FIPs from VMs
        vmname:: Pass specific VM name string to disassociate FIP
        """
        if vmname:
            vmname = self.vm2name
            self._log.info("\nStep: Disassociate FIP from VM %s\n" %(vmname))
            if not self.gbpnova.action_fip_to_vm(
                                          'disassociate',
                                          vmname,
                                          vmfip = self.vm_to_fip[vmname]
                                          ):
               self._log.error(
               "\n///// Disassociating FIP from VM %s failed /////" %(vm))
               return 0
        else:
            self._log.info("\nStep: Disassociate FIPs from all VMs\n")
            for vm,fip in self.vm_to_fip.iteritems():
                if not self.gbpnova.action_fip_to_vm(
                                          'disassociate',
                                          vm,
                                          vmfip = fip
                                          ):
                    self._log.error(
                    "\n//// Disassociating FIP from VM %s failed ////" %(vm))
                    return 0
        if release_fip:
           self.gbpnova.delete_release_fips()
	return 1

    def testApplyUpdatePrsToPtg(self,ptgtype,prs):
        """
        Update Internal PTG & External Pol
        Provide the PolicyRuleSet
        ptgtype:: 'internal' or 'external'
        """
        if ptgtype == 'external':
            self._log.info(
                "\nStep: Updating External Policy by applying Policy RuleSets\n")
            if self.gbpcrud.update_gbp_external_policy(
                                                 self.extpolname,
                                                 consumed_policy_rulesets=[prs]
                                                 ) == 0:
               self._log.error(
               "\n///// Updating External Policy %s failed /////"
               %(self.extpolid))
               return 0
        if ptgtype == 'internal':
           self._log.info(
                "\nStep: Updating Policy Target Group by applying Policy RuleSets\n")
           for ptg in [self.ptg1name, self.ptg2name]:
               if self.gbpcrud.update_gbp_policy_target_group(
                                        ptg,
                                        provided_policy_rulesets=[prs]
                                        ) == 0:
                  self._log.error(
                  "\n///// Updating PTG %s failed /////" %(ptg))
                  return 0
	return 1

    def testCreateNsp(self):
        """
        Create a Network Service Profile
        """
        self._log.info(
                "\nStep: Creating a Network Service Policy")
        self.nspuuid = self.gbpcrud.create_gbp_network_service_policy_for_nat('TestNsp')
        if self.nspuuid == 0:
           return 0
	return 1

    def testApplyRemoveNSpFromPtg(self,nspuuid=''):
        """
        Update to Apply or Remove NSP from Internal PTGs
        """
        if nspuuid == None:
           self._log.info(
             "\nStep: Removing Network Service Policy from Internal PTGs")
           nspuuid = None
        else:
           self._log.info(
             "\nStep: Applying Network Service Policy from Internal PTGs")
           nspuuid = self.nspuuid
        for ptg in [self.ptg1name, self.ptg2name]:
               if self.gbpcrud.update_gbp_policy_target_group(
                                   ptg,
                                   network_service_policy=nspuuid,
                                   ) == 0:
                  self._log.error(
                  "\n///// Updating PTG with NSP %s failed /////" %(ptg))
                  return 0
	return 1

    def testDeleteNatPool(self):
        """
        Deletes all available NAT Pool in the system
        """
        natpool_list = self.gbpcrud.get_gbp_nat_pool_list()
        if len(natpool_list) :
              for natpool in natpool_list:
                 self.gbpcrud.delete_gbp_nat_pool(natpool)
	return 1

    def testTrafficFromExtRtrToVmFip(self,extgwrtr,fip=False):
        """
        Ping and TCP test from external router to VMs
        """
        self._log.info("\nStep: Ping and TCP test from external router\n")
        if fip:
           vmfips = self.vm_to_fip[self.vm1name]
        else:
           vmfips = self.gbpnova.get_floating_ips(ret=1)
	if not vmfips:
		self._log.error(
		"\n///// There are no FIPs to test Traffic /////")
		return 0
        run_traffic = traff_from_extgwrtr(
                                          extgwrtr,
                                          vmfips
                                          )
        if isinstance(run_traffic, dict):
            self._log.error(
            "\n///// Following Traffic Test from External"
            " GW Router Failed == %s /////" % (run_traffic))
            return 0
	return 1
        
    def testTrafficFromVMsToExtRtr(self,extgwips,vmname=True):
        """
        Ping and TCP traffic from VMs to ExtRtr
        """
        if vmname:
            vmlist = [self.vm2name]
        else:
            vmlist = self.vmlist
        self._log.info("\nStep: Ping and TCP traffic from VMs to ExtRtr\n")
        retry = 1
        while retry:
            failed = {}
            for srcvm in vmlist:
                run_traffic = self.nat_traffic.test_traff_anyvm_to_extgw(
                                                      srcvm, extgwips)
                if run_traffic == 2:
                   self._log.error(
                   "\n///// Traffic VM %s Unreachable, Test = Aborted /////"
                   %(srcvm))
                   return 0
                if isinstance(run_traffic, tuple):
                    failed[srcvm] = run_traffic[1]
            if len(failed) and retry == 3:
                self._log.info(
                "\nFollowing Traffic Test Failed After Applying "
                "ICMP-TCP-Combo Contract == %s" % (failed))
                return 0
            elif len(failed) and retry < 3:
               self._log.info("Sleep for 10 sec before retrying traffic")
               sleep(10)
               retry += 1
            else:
               break
	return 1

    def AddSShContract(self,apicip):
        """
        Adds SSH contract between NS and EPG
        Needed for SNAT Tests
        """
        aci=gbpApic(apicip,'gbp')
        self._log.info(
            "\n ADDING SSH-Filter to Svc_epg created for every dhcp_agent")
        svcepglist = [
                'TestPtg1',
                'L2PNat'
                ]
        aci.create_add_filter(svcepglist)
        sleep(15) # TODO: SSH/Ping fails possible its taking time PolicyDownload
	return 1

    def DeleteOrCleanup(self,action,obj=None,uuid=''):
        """
        Specific Delete or Blind Cleanup
        obj & uuid need to be passed ONLY when action='delete'
        """
        if action == 'delete':
           if obj == 'external_segment' and uuid != '':
              self.gbpcrud.delete_gbp_external_segment(uuid)
           elif obj == 'nat_pool' and uuid != '':
              self.gbpcrud.delete_gbp_nat_pool(uuid)
           elif obj == 'external_policy' and uuid != '':
              self.gbpcrud.delete_gbp_external_policy(uuid)
           elif obj == 'policy_target_group' and uuid != '':
              self.gbpcrud.delete_gbp_policy_target_group(uuid)
           else:
              self._log.info("\n Incorrect params passed for delete action")
        if action == 'cleanup':
           self._log.info("\nStep: Blind CleanUp of Resources initiated")
           self._log.info("\nStep: Blind CleanUp: VMs Delete")
           for vm in [self.vm1name, self.vm2name]:
               self.gbpnova.vm_delete(vm)
           self._log.info("\nStep: Blind CleanUp: Release FIPs")
           self.gbpnova.delete_release_fips()
           self._log.info("\nStep: Blind CleanUp: Delete PTs")
           pt_list = self.gbpcrud.get_gbp_policy_target_list()
           if len(pt_list):
              for pt in pt_list:
                self.gbpcrud.delete_gbp_policy_target(pt, property_type='uuid')
           self._log.info("\nStep: Blind CleanUp: Delete PTGs")
           ptg_list = self.gbpcrud.get_gbp_policy_target_group_list()
           if len(ptg_list):
              for ptg in ptg_list:
                self.gbpcrud.delete_gbp_policy_target_group(ptg, property_type='uuid')
           self._log.info("\nStep: Blind CleanUp: Delete L2Ps")
           l2p_list = self.gbpcrud.get_gbp_l2policy_list()
           if len(l2p_list):
              for l2p in l2p_list:
                 self.gbpcrud.delete_gbp_l2policy(l2p, property_type='uuid')
           self._log.info("\nStep: Blind CleanUp: Delete L3Ps")
           l3p_list = self.gbpcrud.get_gbp_l3policy_list()
           if len(l3p_list) :
              for l3p in l3p_list:
                 self.gbpcrud.delete_gbp_l3policy(l3p, property_type='uuid')
           self._log.info("\nStep: Blind CleanUp: Delete NSPs")
           self.gbpcrud.delete_gbp_network_service_policy()
           self._log.info("\nStep: Blind CleanUp: Delete NAT Pools")
           natpool_list = self.gbpcrud.get_gbp_nat_pool_list()
           if len(natpool_list) :
              for natpool in natpool_list:
                 self.gbpcrud.delete_gbp_nat_pool(natpool)
           self._log.info("\nStep: Blind CleanUp: Delete External Pols")
           extpol_list = self.gbpcrud.get_gbp_external_policy_list()
           if len(extpol_list) :
              for extpol in extpol_list:
                 self.gbpcrud.delete_gbp_external_policy(extpol)
           self._log.info("\nStep: Blind CleanUp: Delete Ext Segs")
           extseg_list = self.gbpcrud.get_gbp_external_segment_list()
           if len(extseg_list) :
              for extseg in extseg_list:
                 self.gbpcrud.delete_gbp_external_segment(extseg)
           self._log.info("\nStep: Blind CleanUp of Resources: Completed")
