from common_class import *

steps = resource('aap')
LOG.info("Allowed Address Pair Test starts ..")
#Start of Test Steps
if not steps.create_network_subnet():
	LOG.error("Create Network and Subnet: FAIL")
else:
	LOG.info("Create Network and Subnet: [OK]")
if not steps.create_vm():
	LOG.error("Create VM for AAP: FAIL")
else:
	LOG.info("Create VM for AAP: [OK]")
if not steps.create_aap_port():
	LOG.error("Create AAP Port: FAIL")
else:
	LOG.info("Create AAP Port: [OK]")
if not steps.update_port(enable=True):
	LOG.error("Associate AAP on VM Port: FAIL")
else:
	LOG.info("Associate AAP on VM Port: [OK]")
if not steps.verify_ep():
	LOG.error("Virtual IP of EndPoint has AAP address associated: FAIL")
else:
	LOG.info("Virtual IP of EndPoint has AAP address associated: [OK]")

if not steps.update_port(enable=False):
	LOG.error("Disable AAP on VM Port: FAIL")
else:
	LOG.info("Disable AAP on VM Port: [OK]")
sleep(10)
if not steps.verify_port(False):
	LOG.error("AAP Status on VM Port after disabling: FAIL")
else:
	LOG.info("AAP Status on VM Port after disabling: [OK]")
if not steps.verify_ep(True):
	LOG.error("Promiscuous Mode of EndPoint after disabling: FAIL")
else:
	LOG.info("Promiscuous Mode of EndPoint after disabling: [OK]")
if not steps.update_port(enable=True):
	LOG.error("Enable back AAP on VM Port: FAIL")
else:
	LOG.info("Enable back AAP on VM Port: [OK]")
if not steps.verify_port(True):
	LOG.error("AAP Status VM Port after enabling back: FAIL")
else:
	LOG.info("AAP Status on VM Port after enabling back: [OK]")
sleep(10)
if not steps.verify_ep(False):
	LOG.error("Promiscuous Mode of EndPoint after enbaling back: FAIL")
else:
	LOG.info("Promiscuous Mode of EndPoint after enabling back: [OK]")
    	
steps.cleanup()

