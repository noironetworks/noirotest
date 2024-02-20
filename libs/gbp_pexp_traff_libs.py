#!/usr/bin/env python
import netaddr
import pexpect
import sys
import re
from time import sleep
from testcases.config import conf

NOHUP_OUT = 'nohup: appending output to nohup.out'
SERVER_STRING = '<html> <body> <p>Hello, World!</p> </body> </html>'
NC_PS_STRING = """ps -ef | grep '[n]c -p'| awk -F" " '{print $1}'"""

# Different traffic classes are used, depending on the capabilities
# of the image used for instances. Larger images, with full python
# libraries and networking utilities such as hping3 can conduct more
# sophisticated traffic patterns and tests. Smaller images have to
# rely on lowest-common-denominator utilities such as netcat.
def gbpExpTraff(net_node_ip,netns,src_vm_ip,dst_vm_ip,netns_dict={}):
    if conf.get('no_hping3') and conf['no_hping3'] == 'True':
        return gbpExpTraffNetcat(net_node_ip,netns,src_vm_ip,dst_vm_ip,netns_dict=netns_dict)
    else:
        return gbpExpTraffHping3(net_node_ip,netns,src_vm_ip,dst_vm_ip,netns_dict=netns_dict)

class gbpExpTraffHping3(object):
    """Traffic class for instance images supporting hping3.

    This class is used for traffic testing with instances that have
    python and the hping3 utility.
    """
   
    def __init__(self,net_node_ip,netns,src_vm_ip,dst_vm_ip,netns_dict={}):

        """
        ::pkt_size, if set to JUMBO we will send out 9000
        """
        self.net_node = net_node_ip
        self.netns = netns
        self.src_ep = src_vm_ip
        self.dest_ep = dst_vm_ip
        if not isinstance(self.src_ep,list):
           self.src_ep = [self.src_ep]
        if not isinstance(self.dest_ep,list):
           self.dest_ep = [self.dest_ep]
        self.pkt_cnt = 3
        self.vm_user = 'noiro'
        if conf.get('image_user'):
            self.vm_user = conf['image_user']
        self.vm_password = 'noir0123'
        if conf.get('image_password'):
            self.vm_password = conf['image_password']
        self.host_prompt = '\$'
        self.vm_prompt = '#'
        if conf.get('image_prompt'):
            self.vm_prompt = conf['image_prompt']
        self.netns_dict = netns_dict

    def host_sudo(self, pexpect_session):
        print("Entering sudo priviledged command mode")
        pexpect_session.sendline('sudo -s')
        self.host_prompt = '#'
        pexpect_session.expect(self.host_prompt)

    def ssh_to_compute_host(self):
        self.host_prompt = '\$'
        if conf.get('director_deploy') and conf['director_deploy'] == 'True':
            pexpect_session = pexpect.spawn('ssh heat-admin@%s' %(self.net_node))
            pexpect_session.expect(self.host_prompt) #Expecting passwordless access
        else:
            pexpect_session = pexpect.spawn('ssh root@%s' %(self.net_node))
            pexpect_session.expect(self.host_prompt) #Expecting passwordless access
        pexpect_session.sendline('hostname')
        pexpect_session.expect(self.host_prompt)
        print(pexpect_session.before.decode('utf-8'))
        self.host_sudo(pexpect_session)
        return pexpect_session

    def vm_reachable(self, pexpect_session, ip_list=None, no_ipv6=False):
        for ip in ip_list:
            if isinstance(ip, bytes):
                ip = ip.decode('utf-8')
            ip_type = netaddr.IPAddress(ip)
            if ip_type.version == 6:
                if no_ipv6:
                    continue
                ping_cmd = 'ping6'
            else:
                ping_cmd = 'ping'

            if self.netns_dict.get(ip):
                ns = self.netns_dict[ip]
            else:
                ns = self.netns
            cmd = 'ip netns exec %s %s %s -c 2' %(ns,ping_cmd,ip)
            print(cmd)
            pexpect_session.sendline(cmd) ## Check whether ping works first
            pexpect_session.expect(self.host_prompt)
            print(pexpect_session.before.decode('utf-8'))
            print('Out ==NOIRO')
            if len(re.findall('100% packet loss',pexpect_session.before.decode('utf-8'))): #Count of ping pkts
               print("Cannot run any traffic test since Source VM is Unreachable")
               return 2
        return 0

    def parse_ping_output(self,out,pkt_cnt):
        cnt = pkt_cnt
        output = out
        check = re.search('\\b%s\\b packets transmitted, \\b(\d+)\\b packets received' %(cnt),output,re.I)
        if check != None:
           if int(cnt) - int(check.group(1)) > 1:
              return 0
           else:
              return 1
        else:
            return 0

    def vm_ssh_login(self, pexpect_session, ip_list=None):
        login_retry = 1

        # only use the IPv4 address if dual-stack
        src_ip = None
        for ip in ip_list:
            if isinstance(ip, bytes):
                ip = ip.decode('utf-8')
            ip_type = netaddr.IPAddress(ip)
            if ip_type.version == 4:
                src_ip = ip
                break
        while login_retry < 4:
            try:
                print("Trying to SSH into VM %s....." % src_ip)
                if self.netns_dict.get(src_ip):
                    ns = self.netns_dict[src_ip]
                else:
                    ns = self.netns
                cmd = 'ip netns exec %s ssh %s@%s' %(ns,self.vm_user,src_ip)
                print(cmd)
                pexpect_session.sendline(cmd)
                ssh_newkey = 'Are you sure you want to continue connecting (yes/no)?'
                i = pexpect_session.expect([ssh_newkey,'password:',pexpect.EOF])
                if i == 0:
                    pexpect_session.sendline('yes')
                    i = pexpect_session.expect([ssh_newkey,'password:',pexpect.EOF])
                if i == 1:
                    pexpect_session.sendline(self.vm_password)
                pexpect_session.expect('\$')
                break
            except Exception as e:
                if login_retry == 3:
                    print("After 3 attempts Failed to SSH into the VM from the Namespace\n")
                    print("\nException Error: %s\n" %(e))
                    return 2
            sleep(10)
            login_retry +=1
        return 0

    def vm_scp_file(self, pexpect_session, file_to_scp, ip_list=None):
        login_retry = 1

        # only use the IPv4 address if dual-stack
        src_ip = None
        for ip in ip_list:
            if isinstance(ip, bytes):
                ip = ip.decode('utf-8')
            ip_type = netaddr.IPAddress(ip)
            if ip_type.version == 4:
                src_ip = ip
                break
        while login_retry < 4:
            try:
                print("Trying to SCP file to VM %s....." % src_ip)
                if self.netns_dict.get(src_ip):
                    ns = self.netns_dict[src_ip]
                else:
                    ns = self.netns
                cmd = 'ip netns exec %s scp %s %s@%s:~' %(ns,file_to_scp,self.vm_user,src_ip)
                print(cmd)
                pexpect_session.sendline(cmd)
                ssh_newkey = 'Are you sure you want to continue connecting (yes/no)?'
                i = pexpect_session.expect([ssh_newkey,'password:',pexpect.EOF])
                if i == 0:
                    pexpect_session.sendline('yes')
                    i = pexpect_session.expect([ssh_newkey,'password:',pexpect.EOF])
                if i == 1:
                    pexpect_session.sendline(self.vm_password)
                pexpect_session.expect(self.host_prompt)
                break
            except Exception as e:
                if login_retry == 3:
                    print("After 3 attempts Failed to scp file to the VM from the Namespace\n")
                    print("\nException Error: %s\n" %(e))
                    return 2
            sleep(10)
            login_retry +=1
        return 0


    def vm_sudo(self, pexpect_session):
        pexpect_session.sendline('sudo -s')
        userstring = self.vm_user + ':'
        pexpect_session.expect(userstring)
        pexpect_session.sendline(self.vm_password)
        pexpect_session.expect(self.vm_prompt)

    def vm_test_traffic(self, pexpect_session, protocols, results, tcp_syn_only=0, port=80, no_ipv6=False):
        for dest_ep in self.dest_ep:
            results[dest_ep] = {'icmp':'NA', 'tcp':'NA', 'udp':'NA'} #Setting results for all proto = NA, assuming no traffic is not tested for the specific proto
            for protocol in protocols:
                if protocol=='icmp' or protocol=='all':
                   pexpect_session.sendline('hping3 %s --icmp -c %s --fast -q -d %s' \
                                %(dest_ep,self.pkt_cnt,self.pkt_size))
                   pexpect_session.expect(self.vm_prompt)
                   print("Sent ICMP packets")
                   result=pexpect_session.before.decode('utf-8')
                   print(result)
                   if self.parse_ping_output(result,self.pkt_cnt) !=0:
                      results[dest_ep]['icmp']=1
                   else:
                      results[dest_ep]['icmp']=0
                if protocol=='tcp'or protocol=='all':
                   cmd_s = "sudo hping3 %s -S -V -p %s -c %s --fast -q --tcp-timestamp" \
                            %(dest_ep,port,self.pkt_cnt)
                   cmd_sa = "sudo hping3 %s -S -A -V -p %s -c %s --fast -q --tcp-timestamp" \
                            %(dest_ep,port,self.pkt_cnt)
                   cmd_saf = "sudo hping3 %s -S -A -F -V -p %s -c %s --fast -q --tcp-timestamp" \
                            %(dest_ep,port,self.pkt_cnt)
                   if not tcp_syn_only:
                      for cmd in [cmd_s,cmd_sa,cmd_saf]:
                         pexpect_session.sendline(cmd)
                         pexpect_session.expect(self.vm_prompt)
                         print("Sent TCP SYN,SYN ACK,SYN-ACK-FIN to %s" \
                                %(dest_ep))
                         result=pexpect_session.before.decode('utf-8')
                         print(result)
                         if self.parse_ping_output(result,self.pkt_cnt) !=0:
                            results[dest_ep]['tcp']=1
                         else:
                            # Disregard if we passed SYN, but fail any with ACK
                            # (connection tracking expects SYN only as first packet)
                            if "-A" in cmd and results[dest_ep]['tcp'] == 1:
                               results[dest_ep]['tcp']=1
                            else:
                               results[dest_ep]['tcp']=0
                   else:
                        #Over-riding the label cmd_s,to run simple ncat
                        cmd_s = "nc -w 1 -v %s -z 22" %(dest_ep)
                        pexpect_session.sendline(cmd_s)
                        pexpect_session.expect(self.vm_prompt)
                        result=pexpect_session.before.decode('utf-8')
                        print(result)
                        if 'succeeded' in result:
                            results[dest_ep]['tcp']=1
                        else:
                            results[dest_ep]['tcp']=0
                if protocol=='udp' or protocol=='all':
                    cmd = "hping3 %s --udp -p %s -c %s --fast -q" %(dest_ep,port,self.pkt_cnt)
                    pexpect_session.sendline(cmd)
                    pexpect_session.expect(self.vm_prompt)
                    print('Sent UDP packets')
                    result=pexpect_session.before.decode('utf-8')
                    print(result)
                    if self.parse_ping_output(result,self.pkt_cnt) !=0:
                        results[dest_ep]['udp']=1
                    else:
                        results[dest_ep]['udp']=0

    def test_setup(self, protocols=['icmp','tcp','udp'], no_ipv6=False):
        # This is a no-op for this class
        return 0

    def vm_start_http_server(self, pexpect_session, udp=False):
        if udp:
            return
        pexpect_session.sendline('nohup python -m SimpleHTTPServer 80 &')
        pexpect_session.expect(self.vm_prompt)

    def vm_stop_http_servers(self, pexpect_session):
        print("Stopping SimpleHTTPServer on port 80")
        nc_cmd = """ps -ef | grep [S]imple | awk -F" " '{print $1}'"""
        pexpect_session.sendline(nc_cmd)
        pexpect_session.expect(self.vm_prompt)
        nc_pid=pexpect_session.before.decode('utf-8')
        kill_cmd = 'kill -9 %s' % nc_pid
        pexpect_session.sendline(kill_cmd)
        pexpect_session.expect(self.vm_prompt)

    def validate_metadata(self, pexpect_session, results):
        while False: #TODO: Unless the inherent metadata issue is resolved, no point in executing this part of the code
            pexpect_session.sendline('curl http://169.254.169.254/latest/meta-data')
            pexpect_session.expect(self.vm_prompt)
            meta_result = pexpect_session.before.decode('utf-8')
            print(meta_result)
            if 'hostname' in pexpect_session.before:
                results['metadata']=1
            else:
                results['metadata']=0


    def test_run(self,
                 protocols=['icmp','tcp','udp'],
                 port=80,tcp_syn_only=0,
                 jumbo=0,no_ipv6=False):
        if self.test_setup(protocols=protocols, no_ipv6=no_ipv6):
            return 2
        pexpect_session = self.ssh_to_compute_host()

        if self.vm_reachable(pexpect_session, ip_list=self.src_ep, no_ipv6=no_ipv6):
            return 2
        if self.vm_ssh_login(pexpect_session, ip_list=self.src_ep):
            return 2

        self.vm_sudo(pexpect_session)
        self.vm_start_http_server(pexpect_session)
        if 'udp' in protocols:
            self.vm_start_http_server(pexpect_session, udp=True)
        pexpect_session.sendline('ip addr show eth0')
        pexpect_session.expect(self.vm_prompt)
        # We don't use decode('utf-8') here because the response
        # contains single quotes, which don't decode and causes
        # errors when printing.
        # TODO: try to figure out how to handle this
        print(pexpect_session.before)

        results = {}
        self.validate_metadata(pexpect_session, results)
        if jumbo == 1:
           self.pkt_size = 9000
        else:
           self.pkt_size = 1000

        self.vm_test_traffic(pexpect_session, protocols, results, tcp_syn_only=tcp_syn_only, port=port, no_ipv6=no_ipv6)
        self.vm_stop_http_servers(pexpect_session)
        pexpect_session.close()
        return results

    def run_and_verify_traffic(self,proto,traff_results='',
                               tcp_syn_only=0,jumbo=0,no_ipv6=False
                                ):
        # This method just verify the traffic results
        # OR
        # Can be used to send traffic and verify the results

        if traff_results:
            print('Traffic Results to be analysed == %s' %(traff_results))
            results = traff_results
        else:
            print('Run Traffic for the Protocols: %s and then analyze results' %(proto))
            results = self.test_run(protocols=proto,tcp_syn_only=tcp_syn_only,jumbo=jumbo,no_ipv6=no_ipv6)
        if results == 2:
            return 0
        for dest_ip in self.dest_ep:
            if isinstance(dest_ip, bytes):
                dest_ip = dest_ip.decode('utf-8')
            ip_type = netaddr.IPAddress(dest_ip)
            if no_ipv6 and ip_type.version == 6:
                continue
            allow_list = proto
            result_for_ip = results.get(dest_ip, {})
            failed = {key: val for key, val in result_for_ip.items() if val == 0 and key in allow_list}
            failed.update({key: val for key, val in result_for_ip.items() if val == 1 and key not in allow_list}) 
        if len(failed) > 0:
                print('Following traffic_types %s = Failed' %(failed))
                return 0
        else:
                return 1

    def aap_traff(self,aap_ip):
        """
        aap_ip :: should be ip address of AAP with mask
                  eg: 1.1.1.1/24
        """
        pexpect_session = self.ssh_to_compute_host()
        if self.vm_reachable(pexpect_session, ip_list=self.src_ep, no_ipv6=True):
            return 2

        pkg = 'iputils-arping_20121221-4ubuntu1_amd64.deb'
        if self.vm_scp_file(pexpect_session, pkg, ip_list=self.src_ep):
            return 2
        if self.vm_ssh_login(pexpect_session, ip_list=self.src_ep):
            return 2

        self.vm_sudo(pexpect_session)

        pexpect_session.sendline('dpkg -i %s ' %(pkg))
        pexpect_session.expect(self.vm_prompt)
        pexpect_session.sendline('ip addr show eth0')
        pexpect_session.expect(self.vm_prompt)
        print(pexpect_session.before)
        pexpect_session.sendline('ip addr add %s dev eth0' %(aap_ip))
        pexpect_session.expect(self.vm_prompt)
        print("After adding the AAP-IP to the VM port")
        pexpect_session.sendline('ip addr show eth0')
        pexpect_session.expect(self.vm_prompt)
        print(pexpect_session.before)
        print("Send arping now ....")
        pexpect_session.sendline('arping -c 4 -A -I eth0 %s' %(aap_ip.rstrip('/24')))
        pexpect_session.expect(self.vm_prompt)
        print(pexpect_session.before)
        return 1


class gbpExpTraffNetcat(gbpExpTraffHping3):
    """Traffic class for instance images supporting netcat.

    This class is used for traffic testing with instances that only
    have netcat available to test. It was specifically tested using
    the cirros-0.3.5-x86_64-disk.img image.
    """

    def __init__(self,net_node_ip,netns,src_vm_ip,dst_vm_ip,netns_dict={}):
        self.router_ips = [conf['extrtr_ip1'], conf['extrtr_ip2']]
        self.l3out_ips = [conf['gwip1_extrtr'], conf['gwip2_extrtr']]
        self.ips_to_skip = self.router_ips + self.l3out_ips
        super(gbpExpTraffNetcat, self).__init__(net_node_ip, netns, src_vm_ip,
                                                  dst_vm_ip, netns_dict=netns_dict)

    def vm_sudo(self, pexpect_session):
        print("Entering sudo priviledged command mode")
        pexpect_session.sendline('sudo -s')
        pexpect_session.expect(self.vm_prompt)

    def vm_start_http_server(self, pexpect_session, udp=False):
        print("Starting netcat session on port 80")
        # Create a file to use for the server
        file_cmd = "echo '%s' > index.html" %  SERVER_STRING
        pexpect_session.sendline(file_cmd)
        pexpect_session.expect(self.vm_prompt)
        if udp:
            nc_cmd = 'nohup nc -p 80 -n -u -lk < index.html'
        else:
            nc_cmd = 'nohup nc -p 80 -n -lk < index.html'
        cmdstring = nc_cmd + "&"
        print("HTTP server command is: " + cmdstring)
        pexpect_session.sendline(cmdstring)
        pexpect_session.expect(NOHUP_OUT)

    def vm_stop_http_servers(self, pexpect_session):
        print("Stopping netcat session on port 80")
        nc_cmd = NC_PS_STRING
        pexpect_session.sendline(nc_cmd)
        pexpect_session.expect("}'")
        nc_pid=pexpect_session.before
        print("output from ps is %s" % nc_pid)
        pexpect_session.expect(self.vm_prompt)
        nc_pid=pexpect_session.before
        print("output from ps is %s" % nc_pid)
        for pid in nc_pid.split():
            kill_cmd = 'kill -9 %s' % pid
            pexpect_session.sendline(kill_cmd)
            pexpect_session.expect(self.vm_prompt)

    # Datapath testing relies on servers running in the environment.
    # This method ssh's into each of the destinations and makes sure
    # that the appropriate servers are running, so that they can respond
    # to client requests.
    def test_setup(self, protocols=['icmp','tcp','udp'], no_ipv6=False):
        print("Entered test_setup, dest_ep is %s" % self.dest_ep)
        for dest_ep in self.dest_ep:
            if isinstance(dest_ep, bytes):
                dest_ep = dest_ep.decode('utf-8')
            ip_type = netaddr.IPAddress(dest_ep)
            # skip any IPv6 or external GW IPs
            if ip_type.version == 6 or dest_ep in self.ips_to_skip:
                continue
            print("test_setup: ip %s", dest_ep)
            pexpect_session = self.ssh_to_compute_host()

            # Don't bother with v6 IPs - we just want access to the
            # instance to start the HTTP servers
            if self.vm_reachable(pexpect_session, ip_list=[dest_ep], no_ipv6=True):
                return 2
            if self.vm_ssh_login(pexpect_session, ip_list=[dest_ep]):
                return 2

            self.vm_sudo(pexpect_session)
            # restart the servers
            self.vm_stop_http_servers(pexpect_session)
            self.vm_start_http_server(pexpect_session)
            if 'udp' in protocols:
                self.vm_start_http_server(pexpect_session, udp=True)
            pexpect_session.close()

    def vm_test_traffic(self, pexpect_session, protocols, results, tcp_syn_only=0, port=80, no_ipv6=False):
        for dest_ep in self.dest_ep:
            if isinstance(dest_ep, bytes):
                dest_ep = dest_ep.decode('utf-8')
            ip_type = netaddr.IPAddress(dest_ep)
            if no_ipv6 and ip_type.version == 6:
                continue
            results[dest_ep] = {'icmp':'NA', 'tcp':'NA', 'udp':'NA'} #Setting results for all proto = NA, assuming no traffic is not tested for the specific proto
            for protocol in protocols:
                if protocol=='icmp' or protocol=='all':
                    ping_command = 'ping %s -c %s -s %s' % (dest_ep,
                                                            self.pkt_cnt,
                                                            self.pkt_size)
                    print("ping command: " + ping_command)
                    pexpect_session.sendline(ping_command)
                    pexpect_session.expect(self.vm_prompt)
                    print("Sent ICMP packets")
                    result=pexpect_session.before.decode('utf-8')
                    print("ICMP result: " + result)
                    if self.parse_ping_output(result,self.pkt_cnt) !=0:
                        results[dest_ep]['icmp']=1
                    else:
                        results[dest_ep]['icmp']=0
                if protocol=='tcp'or protocol=='all':
                   if not tcp_syn_only:
                        cmd_s = "echo -e "
                        get_req = "'GET / HTTP/1.1\r\nHost: %s\r\n\r\n'" %(dest_ep)
                        ncat_cmd = " | nc -nvzw 1 %s 80" %(dest_ep)
                        cmd = cmd_s + get_req + ncat_cmd + "&"
                        pexpect_session.sendline(cmd)
                        pexpect_session.expect(self.vm_prompt, timeout=2)
                        print("Sent TCP packets")
                        result=pexpect_session.before.decode('utf-8')
                        print("TCP result: " + result)
                        try:
                            pexpect_session.expect(SERVER_STRING, timeout=2)
                            result=pexpect_session.after.decode('utf-8')
                        except:
                            pass
                        if SERVER_STRING in result:
                            results[dest_ep]['tcp']=1
                        else:
                            results[dest_ep]['tcp']=0
                   else:
                        #Over-riding the label cmd_s,to run simple ncat
                        cmd_s = "nc -w 1 -v %s -z 22 &" %(dest_ep)
                        pexpect_session.sendline(cmd_s)
                        pexpect_session.expect(['SSH', 'timed out'])
                        result=pexpect_session.before.decode('utf-8')
                        print("TCP result: " + result)
                        if 'open' in result:
                            results[dest_ep]['tcp']=1
                        else:
                            results[dest_ep]['tcp']=0
                if protocol=='udp' or protocol=='all':
                    udp_cmd = "nc -w 1 -v -z -u %s 80" %(dest_ep)
                    cmd = udp_cmd + "&"
                    pexpect_session.sendline(cmd)
                    pexpect_session.expect(self.vm_prompt)
                    print('Sent UDP packets')
                    cmd = "fg"
                    pexpect_session.sendline(cmd)
                    pexpect_session.expect(udp_cmd, timeout=2)
                    cmd = "\r\n"
                    pexpect_session.sendline(cmd)
                    result=pexpect_session.after.decode('utf-8')
                    print("UDP result: " + result)
                    try:
                        pexpect_session.expect(SERVER_STRING, timeout=2)
                        result=pexpect_session.after.decode('utf-8')
                    except:
                        pass
                    print(result)
                    # Need to Ctrl-C out of client if still running
                    cmd = "\003"
                    pexpect_session.sendline(cmd)
                    pexpect_session.expect(self.vm_prompt)
                    self.vm_stop_http_servers(pexpect_session)
                    if SERVER_STRING in result:
                        results[dest_ep]['udp']=1
                    else:
                        results[dest_ep]['udp']=0

