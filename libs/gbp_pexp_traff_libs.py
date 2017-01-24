#!/usr/bin/env python
import pexpect
import sys
import re
from time import sleep

class gbpExpTraff(object):
   
    def __init__(self,net_node_ip,netns,src_vm_ip,dst_vm_ip):
        """
        ::pkt_size, if set to JUMBO we will send out 9000
        """
        self.net_node = net_node_ip
        self.netns = netns
        self.src_ep = src_vm_ip
        self.dest_ep = dst_vm_ip
        if not isinstance(self.dest_ep,list):
           self.dest_ep = [self.dest_ep]
        self.pkt_cnt = 3

    def parse_hping(self,out,pkt_cnt):
        cnt = pkt_cnt
        output = out
        check = re.search('\\b%s\\b packets transmitted, \\b(\d+)\\b packets received' %(cnt),output,re.I)
        if check != None:
           if int(cnt) - int(check.group(1)) > 1:
              return 0
        else:
            return 0

    def test_run(self,
	 	 protocols=['icmp','tcp','udp'],
		 port=80,tcp_syn_only=0,
		 jumbo=0):
        child = pexpect.spawn('ssh root@%s' %(self.net_node))
        child.expect('#') #Expecting passwordless access
        child.sendline('hostname')
        child.expect('#')
        print child.before
        child.sendline('ip netns exec %s ping %s -c 2' %(self.netns,self.src_ep)) ## Check whether ping works first
        child.expect('#')
        print child.before
        print 'Out ==NOIRO'
        noicmp,nossh=1,1
        if len(re.findall('Unreachable',child.before))==2: #Count of ping pkts
           noicmp=0       
           print 'I am in No PIng'
        if noicmp==0 :
           print "Cannot run any traffic test since Source VM is Unreachable"
           return 2
        login_retry = 1
        while login_retry < 4: 
            try:
               child.sendline('ip netns exec %s ssh noiro@%s' %(self.netns,self.src_ep))
               ssh_newkey = 'Are you sure you want to continue connecting (yes/no)?'
               i= child.expect([ssh_newkey,'password:',pexpect.EOF])
               if i == 0:
                  child.sendline('yes')
                  i=child.expect([ssh_newkey,'password:',pexpect.EOF])
               if i == 1:
                  child.sendline('noir0123')
               child.expect('\$')
               break
            except Exception as e:
               print "Failing to Login into the VM from the Namespace\n"
               print "\nException Error: %s\n" %(e)
               sleep(10)
               login_retry +=1
        child.sendline('sudo -s')
        child.expect('noiro:')
        child.sendline('noir0123')
        child.expect('#')
	child.sendline('nohup python -m SimpleHTTPServer 80 &')
	child.expect('#')
        child.sendline('ifconfig eth0')
        child.expect('#')
        print child.before
        results = {}
	child.sendline('curl http://169.254.169.254/latest/meta-data')
	child.expect('#')
	if 'hostname' in child.before:
	    results['metadata']=1
	else:
	    results['metadata']=0
        if jumbo == 1:
           self.pkt_size = 9000
        else:
           self.pkt_size = 1000
        for dest_ep in self.dest_ep:
            results[dest_ep] = {'icmp':'NA', 'tcp':'NA', 'udp':'NA'} #Setting results for all proto = NA, assuming no traffic is not tested for the specific proto
            for protocol in protocols:
                if protocol=='icmp' or protocol=='all':
                   child.sendline('hping3 %s --icmp -c %s --fast -q -d %s' %(dest_ep,self.pkt_cnt,self.pkt_size)) #
                   child.expect('#')
                   print "Sent ICMP packets"
                   result=child.before         
                   print result
                   if self.parse_hping(result,self.pkt_cnt) !=0:
                      results[dest_ep]['icmp']=1
                   else:
                      results[dest_ep]['icmp']=0
                if protocol=='tcp'or protocol=='all':
                   cmd_s = "sudo hping3 %s -S -V -p %s -c %s --fast -q" %(dest_ep,port,self.pkt_cnt)
                   cmd_sa = "sudo hping3 %s -S -A -V -p %s -c %s --fast -q" %(dest_ep,port,self.pkt_cnt)
                   cmd_saf = "sudo hping3 %s -S -A -F -V -p %s -c %s --fast -q" %(dest_ep,port,self.pkt_cnt)
                   if not tcp_syn_only:
                      for cmd in [cmd_s,cmd_sa,cmd_saf]:
                         child.sendline(cmd)
                         child.expect('#')
                         print "Sent TCP SYN,SYN ACK,SYN-ACK-FIN to %s" %(dest_ep)
                         result=child.before
                         print result
                         if self.parse_hping(result,self.pkt_cnt) !=0:
                            results[dest_ep]['tcp']=1
                         else:
                            results[dest_ep]['tcp']=0
                   else:
		        #Over-riding the label cmd_s,to run simple ncat
	                cmd_s = "nc -w 1 -v %s -z 22" %(dest_ep)
                        child.sendline(cmd_s)
                        child.expect('#')
                        result=child.before
			print result
                        if 'succeeded' in result:
                            results[dest_ep]['tcp']=1
                        else:
                            results[dest_ep]['tcp']=0
                if protocol=='udp' or protocol=='all':
                   cmd = "hping3 %s --udp -p %s -c %s --fast -q" %(dest_ep,port,self.pkt_cnt)
                   child.sendline(cmd)
                   child.expect('#')
                   print 'Sent UDP packets'
                   result=child.before
                   print result
                   if self.parse_hping(result,self.pkt_cnt) !=0:
                      results[dest_ep]['udp']=1
                   else:
                      results[dest_ep]['udp']=0
        return results 

    def run_and_verify_traffic(self,proto,traff_results='',
			       tcp_syn_only=0,jumbo=0,
				metadata=False):
	# This method just verify the traffic results
	# OR
	# Can be used to send traffic and verify the results

	if traff_results:
            print 'Traffic Results to be analysed == %s' %(traff_results)
	    results = traff_results
	else:
	    print 'Run Traffic for the Protocols: %s and then analyze results' %(proto)
	    results = self.test_run(protocols=proto,tcp_syn_only=tcp_syn_only,jumbo=jumbo)
        if results == 2:
            return results
	for dest_ip in self.dest_ep:
            allow_list = proto
            failed = {key: val for key, val in results[
                dest_ip].iteritems() if val == 0 and key in allow_list}
            failed.update({key: val for key, val in results[
                          dest_ip].iteritems() if val == 1 and key not in allow_list})
	if metadata:
	    if not results['metadata']:
	        failed['metadata']=0
        if len(failed) > 0:
                print 'Following traffic_types %s = Failed' %(failed)
                return 0
        else:
                return 1
	
