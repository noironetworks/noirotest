#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import subprocess
import logging
import sys
from mpcrud.mplibs import config_libs
from mpcrud.mplibs import utils_libs
from mpcrud.mplibs import verify_libs


def main():

    # Run the Testcases:
    test = test_gbp_l2p_func(sys.argv[1])
    if not test.test_gbp_l2p_func_1():
        test.cleanup(tc_name='TESTCASE_GBP_L2P_FUNC_1')
    if not test.test_gbp_l2p_func_2():
        test.cleanup(tc_name='TESTCASE_GBP_L2P_FUNC_2')
    test.cleanup()
    utils_libs.report_results('test_gbp_l2p_func', 'test_results.txt')
    sys.exit(1)


class test_gbp_l2p_func(object):

    # Initialize logging
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        level=logging.WARNING)
    _log = logging.getLogger(__name__)
    cmd = 'rm /tmp/test_gbp_l2p_func.log'
    subprocess.getoutput(cmd)
    hdlr = logging.FileHandler('/tmp/test_gbp_l2p_func.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    _log.addHandler(hdlr)
    _log.setLevel(logging.INFO)
    _log.setLevel(logging.DEBUG)

    def __init__(self,controller_ip):
        """
        Init def
        """
        self._log.info("\n## START OF GBP L3_POLICY FUNCTIONALITY TESTSUITE\n")
        self.gbpcfg = config_libs.Gbp_Config(controller_ip)
        self.gbpverify = verify_libs.Gbp_Verify(controller_ip)
        self.l3p_name = 'demo_l3p'
        self.l2p_name = 'demo_l2p'

    def cleanup(self, tc_name=''):
        if tc_name != '':
            self._log.info('%s: FAILED' % (tc_name))
        for obj in ['group', 'l2p', 'l3p']:
            self.gbpcfg.gbp_del_all_anyobj(obj)

    def test_gbp_l2p_func_1(self):

        self._log.info(
            "\n############################################################\n"
            "TESTCASE_GBP_L2P_FUNC_1: TO CREATE/VERIFY/DELETE/VERIFY "
            "a L2POLICY with DEFAULT ATTRIB VALUE\n"
            "TEST_STEPS::\n"
            "Create L2 Policy Object with default attributes\n"
            "Verify the attributes & value, show & list cmds\n"
            "Verify the implicit neutron network, router, address-scope\n"
            "subnet-pool, L3Policy\n"
            "Delete L2 Policy\n"
            "Verify that L2P,L3P and implicit neutron objects has got "
            "deleted, show & list cmds\n"
            "##############################################################\n")

        # Testcase work-flow starts
        # Create and Verify L2Policy with default attrs(L3Policy & implicit
        # Neutron net obj)
        self._log.info(
            '\n## Step 1: Create L2Policy with default attrib vals##\n')
        uuids = self.gbpcfg.gbp_policy_cfg_all(1, 'l2p', self.l2p_name)
        if not uuids:
            self._log.info("\n## Step 1: Create L2Policy == Failed")
            return 0
        elif len(uuids) < 2:
            self._log.info(
                "\n## Step 1:Create L2Policy Failed due to unexpected "
                "tuple length\n")
            return 0
        else:
            l2p_uuid, def_l3p_uuid, net_uuid, auto_ptg_uuid = uuids
        self._log.info(
            "\n## Step 2: Verify L2Policy, default L3Policy, and Implicit "
            "Neutron objs")
        if not self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                0, 'l2p', l2p_uuid, self.l2p_name):
            self._log.info(
                "\n## Step 2A: Verify L2Policy using -list option == Failed")
            return 0
        if not self.gbpverify.gbp_l2l3ntk_pol_ver_all(
            1,
            'l2p',
            l2p_uuid,
            id=l2p_uuid,
            name=self.l2p_name,
            ret='default',
            l3_policy_id=def_l3p_uuid):
            self._log.info(
                "\n## Step 2B: Verify L2Policy using -show option == Failed")
            return 0
        if not self.gbpverify.neut_ver_all(
                    'net',
                    net_uuid,
                    name='l2p_%s' %
                    (self.l2p_name),
                    admin_state_up='True',
                    status='ACTIVE',
                    shared='False'):
                self._log.info(
                    "\n## Step 2C: Verify implicit neutron network "
                    "object == Failed")
                return 0
        neutron_rtr, neutron_add_scope, neutron_subnetpool=\
                self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                1,
                'l3p',
                def_l3p_uuid,
                name='default',
                id=def_l3p_uuid,
                ret='default',
                l2_policies=l2p_uuid)
        if neutron_rtr or neutron_add_scope or neutron_subnetpool:
            for item,val in {'router':neutron_rtr,
                                   'address-scope':neutron_add_scope,
                                   'subnetpool':neutron_subnetpool}.items():
                if not self.gbpverify.neut_ver_all(item,val):
                    self._log.info(
                    "\n## Step 2D: Verify creation of implicit neutron %s "
                    "object == Failed" %(item))
                    return 0
        else:
            self._log.info(
            "\n## Step 2D: Verify Implcit L3Policy and its Implicit neutron objects == Failed")
            return 0

        # Delete the L2Policy and verify L2P,def l3P and Neutron obj are
        # deleted too
        self._log.info(
            '\n## Step 3: Delete L2Policy and Verify L2P, default L3P and '
            'Implicit Neutron deleted ##\n')
        if not self.gbpcfg.gbp_policy_cfg_all(0, 'l2p', self.l2p_name):
            self._log.info("\n## Step 3: Delete L2Policy == Failed")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(1, 'l2p', l2p_uuid):
            self._log.info(
                "\n## Step 3A: Verify L2Policy is Deleted using -show "
                "option == Failed")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(1, 'l3p', def_l3p_uuid):
            self._log.info(
                "\n## Step 3B: Verify default L3Policy is Deleted == Failed")
            return 0
        if self.gbpverify.neut_ver_all('net', net_uuid):
            self._log.info(
                "\n## Step 3C: Verify Implicit Neutron Network Obj is "
                "Deleted == Failed")
            return 0
        for item,val in {'router':neutron_rtr,
                         'address-scope':neutron_add_scope,
                         'subnetpool':neutron_subnetpool}.items():
                if self.gbpverify.neut_ver_all(item,val):
                    self._log.info(
                    "\n## Step 3D: Verify implicit neutron %s "
                    "object deleted == Failed" %(item))
                    return 0
        self._log.info("\n## TESTCASE_GBP_L2P_FUNC_1: PASSED")
        return 1

    def test_gbp_l2p_func_2(self):

        self._log.info(
            "\n############################################################\n"
            "TESTCASE_GBP_L2P_FUNC_2: TO CREATE/UPDATE/DELETE/VERIFY a "
            "L2POLICY with MULTIPLE PTGs\n"
            "TEST_STEPS::\n"
            "Create L2Policy Object with non-default params\n"
            "Verify the attributes & value, show & list cmds\n"
            "Create Multiple(n=10) PTGs using the above L2P\n"
            "Verify the PTGs and L2P are reflecting in each other in the DB\n"
            "Delete all PTG, L2P\n"
            "Verify that all Implicit Neutron Net/Subnets, default L3P has "
            "got deleted along with PTGs & L2P\n"
            "##############################################################\n")

        # Testcase work-flow starts
        # Create and Verify L2Policy with default attrs(L3Policy & implicit
        # Neutron net obj)
        self._log.info(
            '\n## Step 1: Create L2Policy with default attrib vals##\n')
        uuids = self.gbpcfg.gbp_policy_cfg_all(1, 'l2p', self.l2p_name)
        if not uuids:
            self._log.info("\n## Step 1: Create L2Policy == Failed")
            return 0
        elif len(uuids) < 2:
            self._log.info(
                "\n## Step 1:Create L2Policy Failed due to unexpected "
                "tuple length\n")
            return 0
        else:
            l2p_uuid, def_l3p_uuid = uuids[0], uuids[1]
        self._log.info(
            "\n## Step 2: Verify L2Policy, default L3Policy, and Implicit "
            "Neutron objs")
        net_uuid = self.gbpverify.gbp_l2l3ntk_pol_ver_all(
            1,
            'l2p',
            l2p_uuid,
            ret='default',
            id=l2p_uuid,
            name=self.l2p_name,
            l3_policy_id=def_l3p_uuid)[1]
        if net_uuid and isinstance(net_uuid, str):
            if not self.gbpverify.neut_ver_all(
                    'net',
                    net_uuid,
                    name='l2p_%s' %
                    (self.l2p_name),
                    admin_state_up='True',
                    status='ACTIVE',
                    shared='False'):
                self._log.info(
                    "\n## Step 2A: Verify implicit neutron network "
                    "object == Failed")
                return 0
        else:
            self._log.info(
                "\n## Step 2B: Verify L2Policy using -show option == Failed")
            return 0
        if not self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                1,
                'l3p',
                def_l3p_uuid,
                name='default',
                id=def_l3p_uuid,
                l2_policies=l2p_uuid):
            self._log.info("\n## Step 2C: Verify default L3Policy == Failed")
            return 0
        # Create Multiple PTGs and associate the above L2P
        self._log.info(
            "\n## Step 3: Create Multiple(n=10) PTGs using the above L2P\n")
        n, i = 11, 1
        ptg_list = []
        subnet_list = []
        while i < n:
            ptg_name = 'demo_ptg_%s' % (i)
            uuids = self.gbpcfg.gbp_policy_cfg_all(
                1, 'group', ptg_name, l2_policy=l2p_uuid,
                tenant='coke')
            if uuids:
                ptg_list.append(uuids[0])
                subnet_list.append(uuids[2])
            else:
                self._log.info("\n## Step 3: Create Target-Group == Failed")
                return 0
            if not self.gbpverify.gbp_policy_verify_all(
                1, 'group', ptg_name, id=ptg_list[
                    i - 1], shared='False', l2_policy_id=l2p_uuid):
                self._log.info(
                    "\n## Step 3A: Verify Policy Target-Group "
                    "using L2P == Failed")
                return 0
            if not self.gbpverify.neut_ver_all(
                'subnet', subnet_list[
                    i - 1], network_id=net_uuid):
                self._log.info(
                "\n## Step 3B: Verify Implicit Neutron Subnet == Failed")
                return 0
            i += 1
        if not self.gbpverify.gbp_obj_ver_attr_all_values(
                'l2p', l2p_uuid, 'policy_target_groups', ptg_list):
            self._log.info(
                "\n## Step 3C: Verifying multiple PTGs mapped to "
                "L2P == Failed \n")
            return 0
        # Delete all PTGs and L2P
        self._log.info("\n## Step 4: Delete all PTGs and L2P\n")
        for ptgid in ptg_list:
            if not self.gbpcfg.gbp_policy_cfg_all(0, 'group', ptgid):
                self._log.info("\n## Step 4: Delete Target-Group == Failed")
                return 0
        if not self.gbpcfg.gbp_policy_cfg_all(0, 'l2p', l2p_uuid):
            self._log.info("\n## Step 4A: Delete L2Policy == Failed")
            return 0
        # Verify that all Implicit Neutron Objs, Default L3p , PTGs and L2P are
        # deleted
        self._log.info(
            "\n## Step 5: Verify that all Implicit Neutron Objs, Default L3p, "
            "PTGs and L2P are deleted\n")
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(1, 'l3p', 'default'):
            self._log.info(
                "\n## Step 5: Verify that default L3P has got auto-deleted "
                "== Failed\n")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(1, 'l2p', l2p_uuid):
            self._log.info(
                "\n## Step 5A: Verify that L2P got deleted == Failed\n")
            return 0
        for subnet in subnet_list:
            if self.gbpverify.neut_ver_all('subnet', subnet):
                self._log.info(
                    "\n## Step 5B: Verify that Implicit Neutron Subnet got "
                    "deleted == Failed\n")
                return 0
        for ptgid in ptg_list:
            if self.gbpverify.gbp_policy_verify_all(1, 'group', ptgid):
                self._log.info(
                    "\n## Step 3B: Verify Target-Group is Deleted using "
                    "-show option == Failed")
                return 0
        self._log.info("\n## TESTCASE_GBP_L2P_FUNC_2: PASSED")
        return 1

if __name__ == '__main__':
    main()
