#!/usr/bin/env python  
import optparse
from time import sleep
from fabric.api import cd, run, env, hide, get, settings, local ,put
from fabric.context_managers import *
from testcases.config import conf

L3OUT1=conf.get('primary_L3out')
L3OUT1_NET=conf.get('primary_L3out_net')
L3OUT2=conf.get('secondary_L3out')
L3OUT2_NET=conf.get('secondary_L3out_net')

#Refer this URL for steps:
#https://www.rdoproject.org/blog/2016/11/how-to-install-and-run-tempest/

def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-a", "--action",
                      help="Run or Install, valid string: run <or> ins",
                      default='',
                      dest='action')
    parser.add_option("-c", "--contrlr",
                      help="IP Address of the Ostack Controller",
                      default='',
                      dest='contrlr')
    (options, args) = parser.parse_args()
    if options.contrlr:
        remoteip = options.contrlr
        tempest = Tempest(remoteip)
        if options.action == 'ins':
                tempest.Installjob()
        if options.action == 'run':
                tempest.Runjob()

class Tempest(object):
    def __init__(self,remoteip):
        #remoteip :: should be the controllerIP
        self.remoteip = remoteip
        self.user = 'root'
        self.pwd = 'noir0123'
        
    def Installjob(self):
        env.host_string = self.remoteip
        env.user = self.user
        env.password = self.pwd
        try:
            #Step-1: Install dependencies, pip, clone tempest from GitHub
            for cmd in [
                'yum install -y gcc python-devel libffi-devel openssl-devel',
                'git clone https://github.com/openstack/tempest.git',
                'curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"',
                'python get-pip.py'
                ]:
                run(cmd)
   
            #Step-2: Install venv & tempest in the virtual environment
            run('pip install virtualenv')
            with cd('/root/tempest/'):
                run('virtualenv .venv')
                cmd_src = 'source .venv/bin/activate'
                with prefix(cmd_src):
                    run('pip install -r requirements.txt')
                    run('pip install -r test-requirements.txt')
            run('pip install tempest/')

            #Step-3: Restart the services
            for cmd in [
                'systemctl restart aim-aid',
                'systemctl restart neutron-server'
                ]:
                run(cmd)

            #Step-4: Configure the External-Network
            cmd1 = 'neutron net-create %s' % L3OUT2
            cmd2 = (' ExternalNetwork=uni/tn-common/out-%(l3)s/instP-%(l3net)s'
                    % {'l3': L3OUT2, 'l3net': L3OUT2_NET})
            l3out_cmd = cmd1+\
                        ' --router:external True --shared'+\
                        ' --apic:distinguished_names type=dict'+ cmd2
            cmd1 = 'neutron subnet-create %s 60.60.60.0/24' % L3OUT2
            extsub_cmd = cmd1+\
                 ' --name ext-subnet --disable-dhcp --gateway 60.60.60.1'
            with prefix('source keystonerc_admin'):
                run(l3out_cmd)
                run(extsub_cmd)

            #Step-5: Edit and copy the tempest.conf to the Controller
            #<Following needs Edit in the config>
            # image_ref, image_ref_alt, network_for_ssh,dashboard_url,
            # login_url, uri_v3, uri, public_network_id, floating_network_name
            put('tempest.conf','/root/tempest/etc')
        except Exception as e:
                print("Exception Raised during Tempest Install = ",repr(e)) 
            
            

    def Runjob(self):
        env.host_string = self.remoteip
        env.user = self.user
        env.password = self.pwd
        try:
            with cd('/root/tempest'):
                with prefix('source .venv/bin/activate'):
                     with prefix('source /root/keystonerc_admin'):
                        run('ostestr')
        except Exception as e:
                print("Exception Raised during TempestRun = ",repr(e)) 

if __name__ == "__main__":
    main()
        

