from common_class import *

steps = resource('psec')
LOG.info("Port-Security Test starts ..")
#Start of TestCase-I : Disable/Enable Port-Security on a Port
if not steps.create_network_subnet():
	LOG.error("Create Network and Subnet: FAIL")
else:
	LOG.info("Create Network and Subnet: [OK]")
if not steps.create_vm():
	LOG.error("Create VM for Port-Sec: FAIL")
else:
	LOG.info("Create VM for Port-Sec: [OK]")
if not steps.verify_port(True):
	LOG.error("Port-Security Status on VM Port: FAIL")
else:
	LOG.info("Port-Security Status on VM Port: [OK]")
if not steps.verify_ep(False):
	LOG.error("Promiscuous Mode of the EndPoint: FAIL")
else:
	LOG.info("Promiscuous Mode of the EndPoint: [OK]")
if not steps.update_port(enable=False):
	LOG.error("Disable Port-Security on VM Port: FAIL")
else:
	LOG.info("Disable Port-Security on VM Port: [OK]")
sleep(10)
if not steps.verify_port(False):
	LOG.error("Port-Security Status on VM Port after disabling: FAIL")
else:
	LOG.info("Port-Security Status on VM Port after disabling: [OK]")
if not steps.verify_ep(True):
	LOG.error("Promiscuous Mode of EndPoint after disabling: FAIL")
else:
	LOG.info("Promiscuous Mode of EndPoint after disabling: [OK]")
if not steps.update_port(enable=True):
	LOG.error("Enable back Port-Security on VM Port: FAIL")
else:
	LOG.info("Enable back Port-Security on VM Port: [OK]")
if not steps.verify_port(True):
	LOG.error("Port-Security Status VM Port after enabling back: FAIL")
else:
	LOG.info("Port-Security Status on VM Port after enabling back: [OK]")
sleep(10)
if not steps.verify_ep(False):
	LOG.error("Promiscuous Mode of EndPoint after enabling back: FAIL")
else:
	LOG.info("Promiscuous Mode of EndPoint after enabling back: [OK]")

#Partial Clean-up    	
steps.cleanup(resourceOnly=True)

#Start of TestCase-II : Disable/Enable Port-Security on Network
if not steps.create_network_subnet(repeat=True):
	LOG.error("Create Network and Subnet with PortSec Disabled: FAIL")
else:
	LOG.info("Create Network and Subnet with PortSec Disabled: [OK]")
# Nova always tries to add default security group to port of instance even 
# if port has port security disabled, in this case, security group applying
# fails, further causing instance launching fails
sleep(5)
if steps.create_vm():
	LOG.error("Create VM must fail: FAIL") 
else:
	LOG.info("Create VM must fail: [OK]")

#Full Clean-up    	
steps.cleanup()
