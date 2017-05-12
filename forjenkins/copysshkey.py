#!/usr/bin/env python
import pexpect
from testcases.config import conf

CNTRLRIP = conf['controller_ip']
NTKNODE = conf['network_node']
COMP2 = conf['compute-2']
PASSWD = 'noir0123'

def ssh_copy_id(hostname):
    child = pexpect.spawn('ssh-copy-id root@%s' %(hostname))
    try:
	index = child.expect(['continue connecting \(yes/no\)','\'s password:',pexpect.EOF],timeout=8)
	if index == 0:
	    child.sendline('yes')
	    #child.expect('password:')
	    ret1 = child.expect(["password:",pexpect.EOF])
	    if ret1 == 0:
	        child.sendline(PASSWD)
	elif index == 1:
	    child.sendline(PASSWD)
	    child.expect('$')
	else:
	    pass
	child.close()
    except pexpect.TIMEOUT:
	child.close()

for host in [CNTRLRIP,NTKNODE,COMP2]:
    ssh_copy_id(host)
