from common_class import *

steps = resource('aap')
LOG.info("Allowed Address Pair Test starts ..")
#Start of Test Steps
if not steps.create_network_subnet():
	LOG.error("Step: Create Network and Subnet: FAIL")
else:
	LOG.info("Step: Create Network and Subnet: [OK]")
if not steps.create_vm():
	LOG.error("Step: Create VM for AAP: FAIL")
else:
	LOG.info("Step: Create VM for AAP: [OK]")
if not steps.create_aap_port():
	LOG.error("Step: Create AAP Port: FAIL")
else:
	LOG.info("Step: Create AAP Port: [OK]")
if not steps.update_port(enable=True):
	LOG.error("Step: Associate AAP on VM Port: FAIL")
else:
	LOG.info("Step: Associate AAP on VM Port: [OK]")
if not steps.verify_ep(aap_set=False):
	LOG.error("Step: Virtual IP of EndPoint has AAP address associated: FAIL")
else:
	LOG.info("Step: Virtual IP of EndPoint has AAP address associated: [OK]")
if not steps.send_traff_for_aap():
	LOG.error("Generate AAP Traffic using ARP-Ping: FAIL")
else:
	LOG.info("Generate AAP Traffic using ARP-Ping: [OK]")
if not steps.verify_ep(aap_vm=steps.vm1):
	LOG.error("Step: Real IP of EndPoint has AAP address associated: FAIL")
else:
	LOG.info("Step: Real IP of EndPoint has AAP address associated: [OK]")
if not steps.update_port(enable=False):
	LOG.error("Step: Disable AAP on VM Port: FAIL")
else:
	LOG.info("Step: Disable AAP on VM Port: [OK]")
sleep(10)
if not steps.verify_ep(aap_set=False):
	LOG.error("Step: Virtual IP of EndPoint has AAP address associated: FAIL")
else:
	LOG.info("Step: Virtual IP of EndPoint has AAP address associated: [OK]")
"""
if not steps.verify_ep(True):
	LOG.error("Promiscuous Mode of EndPoint after disabling: FAIL")
else:
	LOG.info("Promiscuous Mode of EndPoint after disabling: [OK]")
if not steps.update_port(enable=True):
	LOG.error("Enable back AAP on VM Port: FAIL")
else:
	LOG.info("Enable back AAP on VM Port: [OK]")
if not steps.verify_port(True):
	LOG.error("Step: AAP Status VM Port after enabling back: FAIL")
else:
	LOG.info("Step: AAP Status on VM Port after enabling back: [OK]")
sleep(10)
if not steps.verify_ep(False):
	LOG.error("Promiscuous Mode of EndPoint after enbaling back: FAIL")
else:
	LOG.info("Promiscuous Mode of EndPoint after enabling back: [OK]")
"""    	
steps.cleanup()

