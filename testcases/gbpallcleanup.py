#!/usr/bin/python

from commands import *
import datetime
import logging
import sys
import yaml
from time import sleep
from libs.gbp_aci_libs import GbpApic
from libs.gbp_crud_libs import GBPCrud
from libs.gbp_nova_libs import gbpNova

Log = logging.getLogger(__name__)
Log.setLevel(logging.INFO)
# create a logfile handler
hdlr = logging.FileHandler('/tmp/gbpcleanup')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)
# Add the handler to the logger
Log.addHandler(hdlr)

class GbpAllCleanup(object):

    def __init__(self,cntlrip,apicip):
        self.gbpcrud = GBPCrud(cntlrip)
        self.gbpnova = gbpNova(cntlrip)
	self.gbpapic = GbpApic(apicip,'gbp')

    def cleanupAll(self):
           Log.info("\nStep: Blind CleanUp to be executed")
           Log.info("\nStep: Blind CleanUp: Delete PTs")
           pt_list = self.gbpcrud.get_gbp_policy_target_list()
	   print 'Inside the cleanupAll'
           if len(pt_list) > 0:
              for pt in pt_list:
                self.gbpcrud.delete_gbp_policy_target(pt, property_type='uuid')
           Log.info("\nStep: Blind CleanUp: Delete PTGs")
           ptg_list = self.gbpcrud.get_gbp_policy_target_group_list()
           if len(ptg_list) > 0:
              for ptg in ptg_list:
                self.gbpcrud.delete_gbp_policy_target_group(ptg, property_type='uuid')
           Log.info("\nStep: Blind CleanUp: Delete L2Ps")
           l2p_list = self.gbpcrud.get_gbp_l2policy_list()
           if len(l2p_list) > 0:
              for l2p in l2p_list:
                 self.gbpcrud.delete_gbp_l2policy(l2p, property_type='uuid')
           Log.info("\nStep: Blind CleanUp: Delete L3Ps")
           l3p_list = self.gbpcrud.get_gbp_l3policy_list()
           if len(l3p_list) > 0:
              for l3p in l3p_list:
                 self.gbpcrud.delete_gbp_l3policy(l3p, property_type='uuid')
           Log.info("\nStep: Blind CleanUp: Delete NSPs")
           self.gbpcrud.delete_gbp_network_service_policy()
           Log.info("\nStep: Blind CleanUp: Delete NAT Pools")
	   print 'Inside the cleanupAll'
           natpool_list = self.gbpcrud.get_gbp_nat_pool_list()
           if len(natpool_list) > 0:
              for natpool in natpool_list:
                 self.gbpcrud.delete_gbp_nat_pool(natpool)
           Log.info("\nStep: Blind CleanUp: Delete External Pols")
           extpol_list = self.gbpcrud.get_gbp_external_policy_list()
           if len(extpol_list) > 0:
              for extpol in extpol_list:
                 self.gbpcrud.delete_gbp_external_policy(extpol)
           Log.info("\nStep: Blind CleanUp: Delete Ext Segs")
           extseg_list = self.gbpcrud.get_gbp_external_segment_list()
           if len(extseg_list) > 0:
              for extseg in extseg_list:
                 self.gbpcrud.delete_gbp_external_segment(extseg)
	   Log.info("\nStep: Blind CleanUp: Tenants from ACI")
	   self.gbpapic.deletetenants()

def main():
    cfgfile = sys.argv[1]
    with open(cfgfile, 'rt') as f:
	conf = yaml.load(f)
    controllerIp = conf['controller_ip']
    apicIp = conf['apic_ip']
    Log.info("controllerIp == %s" %(controllerIp))
    Log.info("ApicIp == %s" %(apicIp))
    #sys.exit(1)
    clean = GbpAllCleanup(controllerIp,apicIp)
    clean.cleanupAll()

if __name__ == "__main__":
   main()

