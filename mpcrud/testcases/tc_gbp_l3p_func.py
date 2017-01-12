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

import commands
import logging
import platform
import sys

from libs import config_libs
from libs import utils_libs
from libs import verify_libs


def main():

    # Run the Testcases:
    test = test_gbp_l3p_func()
    if test.test_gbp_l3p_func_1() == 0:
        test.cleanup(tc_name='TESTCASE_GBP_L3P_FUNC_1')
    if test.test_gbp_l3p_func_2() == 0:
        test.cleanup(tc_name='TESTCASE_GBP_L3P_FUNC_2')
    if test.test_gbp_l3p_func_3() == 0:
        test.cleanup(tc_name='TESTCASE_GBP_L3P_FUNC_3')
    if test.test_gbp_l3p_func_4() == 0:
        test.cleanup(tc_name='TESTCASE_GBP_L3P_FUNC_4')
    test.cleanup()
    utils_libs.report_results('test_gbp_l3p_func', 'test_results.txt')
    sys.exit(1)


class test_gbp_l3p_func(object):

    # Initialize logging
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        level=logging.WARNING)
    _log = logging.getLogger(__name__)
    cmd = 'rm /tmp/test_gbp_l3p_func.log'
    commands.getoutput(cmd)
    hdlr = logging.FileHandler('/tmp/test_gbp_l3p_func.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    _log.addHandler(hdlr)
    _log.setLevel(logging.INFO)
    _log.setLevel(logging.DEBUG)

    def __init__(self):
        """
        Init def
        """
        self._log.info("\n## START OF GBP L3_POLICY FUNCTIONALITY TESTSUITE\n")
        self.gbpcfg = config_libs.Gbp_Config('10.30.120.117')
        self.gbpverify = verify_libs.Gbp_Verify('10.30.120.117')
        self.l3p_name = 'demo_l3p'
        self.l2p_name = 'demo_l2p'

    def cleanup(self, tc_name=''):
        if tc_name != '':
            self._log.info('## %s: FAILED' % (tc_name))
        for obj in ['group', 'l2p', 'l3p']:
            self.gbpcfg.gbp_del_all_anyobj(obj)

    def test_gbp_l3p_func_1(
            self,
            name_uuid='',
            l3p_uuid='',
            rep_cr=0,
            rep_del=0):

        if rep_cr == 0 and rep_del == 0:
            self._log.info(
                "\n########################################################\n"
                "TESTCASE_GBP_L3P_FUNC_1: TO CREATE/VERIFY/DELETE/VERIFY a "
                "L3POLICY with DEFAULT ATTRIB VALUE\n"
                "TEST_STEPS::\n"
                "Create L3 Policy Object\n"
                "Verify the attributes & value, show & list cmds\n"
                "Verify the implicit neutron objects: rtr,add_scope,subpool\n"
                "Delete L3 Policy Object\n"
                "Verify that PR and implicit neutron objects has got "
                "deleted, show & list cmds\n"
                "##########################################################\n")

        if name_uuid == '':
            name_uuid = self.l3p_name
        # Testcase work-flow starts
        if rep_cr == 0 or rep_cr == 1:
            self._log.info(
                '\n## Step 1: Create L3Policy with default attrib vals##\n')
            l3p_uuid,addr_scope_uuid,subpool_uuid,rtr_uuid = \
		self.gbpcfg.gbp_policy_cfg_all(1, 'l3p', name_uuid)
            if l3p_uuid == 0:
                self._log.info("\n## Step 1: Create L3Policy == Failed")
                return 0
            self._log.info('# Step 2A: Verify L3Policy using -list cmd')
            if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                    0, 'l3p', l3p_uuid, name_uuid) == 0:
                self._log.info(
                    "\n## Step 2A: Verify L3Policy using -list option "
                    "== Failed")
                return 0
            self._log.info('# Step 2B: Verify L3Policy using -show cmd')
            if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                        1,
                        'l3p',
                        l3p_uuid,
                        id=l3p_uuid,
                        name=name_uuid,
                        subnet_prefix_length='24',
                        ip_version='4') == 0:
                    self._log.info(
                        "\n## Step 2C: Verify L3Policy using -show "
                        "option == Failed")
                    return 0
	    self._log.info('# Step 2C: Verify implicit Neutron objects rtr,addscope,subpool')
            if rtr_uuid or addr_scope_uuid or subpool_uuid:
                for item,val in {'router': rtr_uuid,
                                   'address-scope': addr_scope_uuid,
                                   'subnetpool': subpool_uuid}.iteritems():
                    if not self.gbpverify.neut_ver_all(item,val):
                        self._log.info(
                        "\n## Step 2C: Verify implicit neutron %s "
                        "object == Failed" %(item))
                        return 0
	    else:
		self._log.info('# Step 2C:Creation of implicit Neutron object failed')
		return 0
        #######
        if rep_del == 0 or rep_del == 1:
            self._log.info('\n## Step 3: Delete L3Policy using name  ##\n')
            if self.gbpcfg.gbp_policy_cfg_all(0, 'l3p', name_uuid) == 0:
                self._log.info("\n## Step 3: Delete L3Policy == Failed")
                return 0
            if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                    0, 'l3p', name_uuid, l3p_uuid) != 0:
                self._log.info(
                    "\n## Step 3A: Verify L3Policy is Deleted using "
                    "-list option == Failed")
                return 0
            if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                    1, 'l3p', name_uuid, l3p_uuid) != 0:
                self._log.info(
                    "\n## Step 3B: Verify L3Policy is Deleted using "
                    "-show option == Failed")
                return 0
            if rep_cr == 0 and rep_del == 0:
                self._log.info("\n## TESTCASE_GBP_L3P_FUNC_1: PASSED")
        return 1

    def test_gbp_l3p_func_2(self):

        self._log.info(
            "\n############################################################\n"
            "TESTCASE_GBP_L3P_FUNC_2: TO CREATE/UPDATE/DELETE/VERIFY a "
            "L3POLICY with EDITABLE ATTRs\n"
            "TEST_STEPS::\n"
            "Create L3Policy Object with non-default params\n"
            "Verify the attributes & value, show & list cmds\n"
            "Update the L3Policy Objects\n"
            "Verify the attributes & value, show & list cmds\n"
            "Delete L3Policy using Name\n"
            "Verify that L3P has got deleted, show & list cmds\n"
            "##############################################################\n")

        # Testcase work-flow starts
        self._log.info(
            "\n## Step 1: Create Policy L3Policy with non-default "
            "attrs and values ##")
	l3p_uuid,addr_scope_uuid,subpool_uuid,rtr_uuid = \
            self.gbpcfg.gbp_policy_cfg_all(
            1, 'l3p', self.l3p_name, ip_pool='20.20.0.0/24',
            subnet_prefix_length='28')
        if l3p_uuid == 0:
            self._log.info("\n## Step 1: Create L3Policy == Failed")
            return 0
        self._log.info('\n## Step 2B: Verify L3Policy using -show cmd')
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                    1,
                    'l3p',
                    l3p_uuid,
                    id=l3p_uuid,
                    name=self.l3p_name,
                    ip_pool='20.20.0.0/24',
                    subnet_prefix_length='28',
                    ip_version='4') == 0:
                self._log.info(
                    "\n## Step 2B: Verify L3Policy using -show option"
                    " == Failed")
	self._log.info('# Step 2C:Verify the creation of implicit Neutron objs')
        if rtr_uuid or addr_scope_uuid or subpool_uuid:
                for item,val in {'router': rtr_uuid,
                                   'address-scope': addr_scope_uuid,
                                   'subnetpool': subpool_uuid}.iteritems():
                    if not self.gbpverify.neut_ver_all(item,val):
                        self._log.info(
                        "\n## Step 2C: Verify implicit neutron %s "
                        "object == Failed" %(item))
                        return 0
	else:
		self._log.info('# Step 2C:Creation of implicit Neutron object failed')
		return 0

        if self.gbpcfg.gbp_policy_cfg_all(
                2, 'l3p', self.l3p_name, subnet_prefix_length='26') == 0:
            self._log.info(
                "\n## Step 3: UPdating L3Policy attributes == Failed")
            return 0
        self._log.info(
            "\n## Step 3: Verify that Updated Attributes in L3Policy")
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                1,
                'l3p',
                self.l3p_name,
                id=l3p_uuid,
                name=self.l3p_name,
                ip_pool='20.20.0.0/24',
                subnet_prefix_length='26',
                ip_version='4') == 0:
            self._log.info(
                "\n## Step 3: Verify L3Policy using -show option == Failed")
        self.test_gbp_l3p_func_1(name_uuid=l3p_uuid, rep_cr=2)
        self._log.info("\n## TESTCASE_GBP_L3P_FUNC_2: PASSED")
        return 1

    def test_gbp_l3p_func_3(self):

        self._log.info(
            "\n############################################################\n"
            "TESTCASE_GBP_L3P_FUNC_3: TO CREATE/UPDATE/DELETE/VERIFY "
            "L3POLICY AND ASSOCIATED L2POLICY\n"
            "TEST_STEPS::\n"
            "Create L3Policy with defined attributes\n"
            "Create L2Policy with default attributes\n"
            "Update L2Policy to change the from default to the above "
            "non-default L3Policy\n"
            "Verify the Update of L3Policy attribute of L2Policy fails\n"
            "Update L3Policy(default) editable attributes\n"
            "Delete the L2Policy(this causes auto-delete of default-L3Pol)\n"
            "Verify L3/L2Policies successfully deleted\n"
            "##############################################################\n")

        # Testcase work-flow starts
        # Create L2 L3 Policy
        self._log.info(
            "\n## Step 1: Create L3Policy with non-default attrs and "
            "values ##")
        l3p_uuid = self.gbpcfg.gbp_policy_cfg_all(
            1, 'l3p', self.l3p_name, ip_pool='20.20.0.0/24',
            subnet_prefix_length='28',
            proxy_ip_pool='192.167.0.0/16')[0]
        if l3p_uuid == 0:
            self._log.info("\n## Step 1: Create L3Policy == Failed")
            return 0
        self._log.info(
            '\n## Step 1A: Create L2Policy with default attributes##\n')
        l2p = self.gbpcfg.gbp_policy_cfg_all(1, 'l2p', self.l2p_name)
        if not l2p:
            self._log.info(
                "\n## New L2Policy Create Failed, hence "
                "Testcase_gbp_l3p_func_3 ABORTED\n")
            return 0
        else:
            l2p_uuid, def_l3p_uuid = l2p[0], l2p[1]
        # Associating L2Policy with non-default L3Policy(should Fail) and
        # UPdating the L3Policy(in-use/default)
        if self.gbpcfg.gbp_policy_cfg_all(
                2, 'l2p', self.l2p_name, l3_policy_id=l3p_uuid) != 0:
            self._log.info(
                "\n## Updating/Changing L3Policy attribute of "
                "L2Policy did NOT Fail")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                1, 'l2p', self.l2p_name, l3_policy_id=def_l3p_uuid) == 0:
            self._log.info(
                "\n## Step 3A: Verify L2Policy is still associated to "
                "its  default L3Policy == Failed")
            return 0
        if self.gbpcfg.gbp_policy_cfg_all(
                2, 'l3p', def_l3p_uuid, subnet_prefix_length='27') == 0:
            self._log.info(
                "\n## Step 4: UPdating default L3Policy's "
                "attributes == Failed")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                1,
                'l3p',
                def_l3p_uuid,
                id=def_l3p_uuid,
                ip_pool='112.112.0.0/16',
                l2_policies=l2p_uuid,
                subnet_prefix_length='27',
                ip_version='4') == 0:
            self._log.info(
                "\n## Step 4A: Verify L3Policy after associating "
                "to the L2Policy == Failed")
            return 0

        # Delete L2/L3 Policies
        if self.gbpcfg.gbp_policy_cfg_all(0, 'l2p', l2p_uuid) == 0:
            self._log.info("\n## Step 5: Delete L2Policy == Failed")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(1, 'l2p', l2p_uuid) != 0:
            self._log.info("\n## Step 5A: Verify Delete of L2Policy == Failed")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(1, 'l3p', def_l3p_uuid) != 0:
            self._log.info(
                "\n## Step 5B: Verify Auto-Delete of default "
                "L3Policy == Failed")
            return 0
        self._log.info("\n## TESTCASE_GBP_L3P_FUNC_3: PASSED")
        return 1

    def test_gbp_l3p_func_4(self):

        self._log.info(
            "\n############################################################\n"
            "TESTCASE_GBP_L3P_FUNC_4: TO CREATE/UPDATE/DELETE/VERIFY "
            "MULTI L2POLICY to SINGLE L3POLICY\n"
            "TEST_STEPS::\n"
            "Create non-default L3Policy with defined attributes\n"
            "Create Multiple L2Policies with above non-default L3policy\n"
            "Verify that L2Policies are created with non-default L3Policy\n"
            "Delete all L2 Policies\n"
            "Verify that non-default L3 Policy exists but with null "
            "L2Policies\n"
            "Delete the L3Policy\n"
            "Verify L3/L2Policys successfully deleted\n"
            "##############################################################\n")

        # Testcase work-flow starts
        # Create and Verify non-default L3 Policy
        self._log.info(
            "\n## Step 1: Create Policy L3Policy with non-default "
            "attrs and values ")
        l3p_uuid = self.gbpcfg.gbp_policy_cfg_all(
            1, 'l3p', self.l3p_name, ip_pool='40.50.0.0/24',
            subnet_prefix_length='28')[0]
        if l3p_uuid == 0:
            self._log.info("\n## Step 1: Create L3Policy == Failed")
            return 0
        if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                1,
                'l3p',
                l3p_uuid,
                id=l3p_uuid,
                name=self.l3p_name,
                ip_pool='40.50.0.0/24',
                subnet_prefix_length='28',
                ip_version='4') == 0:
            self._log.info("\n## Step 1A: Verify non-default == Failed")
            return 0
        # Create and verify multiple L2 policy with above non-default L3P
        self._log.info(
            "\n## Step 2: Create and Verify multiple(n=10) L2Policy "
            "associated with 1 non-default L3P")
        l2p_uuid_list = []
        n, i = 11, 1
        while i < n:
            l2p_name = 'demo_l2p_%s' % (i)
            l2p = self.gbpcfg.gbp_policy_cfg_all(
                1, 'l2p', l2p_name, l3_policy_id=l3p_uuid)
            if l2p == 0:
                self._log.info(
                    "\n## Step 2B:New L2Policy Create Failed, hence "
                    "Testcase_gbp_l3p_func_4 ABORTED\n")
                return 0
            elif len(l2p) < 2:
                self._log.info(
                    "\n## Step 2C: New L2Policy Create Failed due to "
                    "unexpected tuple length\n")
                return 0
            else:
                l2p_uuid = l2p[0]
                l2p_uuid_list.append(l2p_uuid)
            if self.gbpverify.gbp_l2l3ntk_pol_ver_all(
                    1, 'l2p', l2p_name, id=l2p_uuid,
                    l3_policy_id=l3p_uuid) == 0:
                self._log.info(
                    "\n## Step 2D: Verify L2Policy using non-default "
                    "L3P == Failed")
                return 0
            i += 1
        # Verify that non-default L3P has all the above create L2Ps
        if self.gbpverify.gbp_obj_ver_attr_all_values(
                'l3p', l3p_uuid, 'l2_policies', l2p_uuid_list) == 0:
            self._log.info(
                "\n## Step 2E: Verifying multiple L2Ps mapped to "
                "non-default L3P == Failed \n")
            return 0
        # Delete all L2Ps and verify that non-default L3P has null L2Ps
        self._log.info(
            "\n## Step 3: Delete all L2Ps and verify that non-default "
            "L3P has no L2P associated\n")
        for l2pid in l2p_uuid_list:
            if self.gbpcfg.gbp_policy_cfg_all(0, 'l2p', l2pid) == 0:
                self._log.info(
                    "\n## Step 3: Delete of L2P %s == Failed\n" %
                    (l2pid))
                return 0
            if self.gbpverify.gbp_l2l3ntk_pol_ver_all(1, 'l2p', l2pid) != 0:
                self._log.info(
                    "\n## Step 3A: Verify that L2P got deleted == Failed\n")
                return 0
        if self.gbpverify.gbp_obj_ver_attr_all_values(
                'l3p', l3p_uuid, 'l2_policies', l2p_uuid_list) != 0:
            self._log.info(
                "\n## Step 3B: Verifying Non-Default L3P has no more "
                "L2P mapped == Failed \n")
            return 0
        self.test_gbp_l3p_func_1(name_uuid=l3p_uuid, rep_cr=2)
        self._log.info("\n## TESTCASE_GBP_L3P_FUNC_4: PASSED")
        return 1

if __name__ == '__main__':
    main()
