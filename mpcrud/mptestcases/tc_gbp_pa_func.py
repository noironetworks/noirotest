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
import os
import re
import sys

from mpcrud.mplibs import config_libs
from mpcrud.mplibs import utils_libs
from mpcrud.mplibs import verify_libs


def main():

    # Run the Testcase:
    test = test_gbp_pa_func(sys.argv[1])
    test.test_cr_ver_del_ver_default()
    utils_libs.report_results('test_gbp_pa_func', 'test_results.txt')
    sys.exit(1)


class test_gbp_pa_func(object):

    # Initialize logging
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        level=logging.WARNING)
    _log = logging.getLogger(__name__)
    cmd = 'rm /tmp/test_gbp_pa_func.log'
    subprocess.getoutput(cmd)
    hdlr = logging.FileHandler('/tmp/test_gbp_pa_func.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    _log.addHandler(hdlr)
    _log.setLevel(logging.INFO)
    _log.setLevel(logging.DEBUG)

    def __init__(self,controller_ip):
        """
        Init def
        """
        self._log.info(
            "\n## START OF GBP POLICY_ACTION FUNCTIONALITY TESTSUITE\n")
        self.gbpcfg = config_libs.Gbp_Config(controller_ip)
        self.gbpverify = verify_libs.Gbp_Verify(controller_ip)
        self.act_name = 'demo_act'

    def cleanup(self, cfgobj, uuid_name, tc_name=''):
        if tc_name != '':
            self._log.info('%s FAILED' % (tc_name))
        if isinstance(cfgobj, str):
            cfgobj = [cfgobj]
        if isinstance(uuid_name, str):
            uuid_name = [uuid_name]
        for obj, _id in zip(cfgobj, uuid_name):
            if self.gbpcfg.gbp_policy_cfg_all(0, obj, _id):
                self._log.info(
                    'Success in Clean-up/Delete of Policy Object %s\n' %
                    (obj))
            else:
                self._log.info(
                    'Failed to Clean-up/Delete of Policy Object %s\n' %
                    (obj))
        os._exit(1)

    def test_cr_ver_del_ver_default(self, rep_cr=0, rep_del=0):

        if rep_cr == 0 and rep_del == 0:
            self._log.info(
                "\n###################################################\n"
                "TESTCASE_GBP_PA_FUNC_1: CREATE/VERIFY/DELETE/VERIFY a "
                "POLICY ACTION with DEFAULT ATTR VALUE\n"
                "TEST_STEPS:\n"
                "Create Policy Action Object,default params\n"
                "Verify the attributes & value, show & list cmds\n"
                "Delete Policy Action using Name\n"
                "Verify that PA has got deleted, show & list cmds\n"
                "Recreate Policy Action Object inorder to test Delete "
                "using UUID\n"
                "Delete using UUID\n"
                "Verify that PA has got deleted, show & list cmds\n"
                "###################################################\n")

        # Testcase work-flow starts
        self._log.info(
            '\n## Step 1: Create Action with default attrib values##\n')
        act_uuid = self.gbpcfg.gbp_action_config(1, self.act_name)
        if act_uuid == 0:
            self._log.info("# Step 1: Create Action == Failed")
            return 0
        if self.gbpverify.gbp_action_verify(0, self.act_name, act_uuid) == 0:
            self._log.info(
                "# Step 2A: Verify Action using -list option == Failed")
            return 0
        if self.gbpverify.gbp_action_verify(
                1,
                self.act_name,
                id=act_uuid,
                action_type='allow',
                shared='False') == 0:
            self._log.info(
                "# Step 2B: Verify Action using -show option == Failed")
            return 0
        ######
        self._log.info('\n## Step 3: Delete Action using name ##\n')
        if self.gbpcfg.gbp_action_config(0, self.act_name) == 0:
            self._log.info("# Step 3: Delete Action using Name == Failed")
            return 0
        if self.gbpverify.gbp_action_verify(0, self.act_name, act_uuid) != 0:
            self._log.info(
                "\n## Step 3A: Verify Action is Deleted using -list option "
                "== Failed")
            return 0
        if self.gbpverify.gbp_action_verify(
                1,
                self.act_name,
                id=act_uuid,
                action_type='allow',
                shared='False') != 0:
            self._log.info(
                "\n## Step 3B: Verify Action is Deleted using -show option "
                "== Failed")
            return 0

        act_uuid = self.gbpcfg.gbp_action_config(1, self.act_name)
        if act_uuid:
            self._log.info(
                "Step 4: Re-created a Policy Action with default inorder "
                "to delete with ID")
            self._log.info('\n## Step 5: Delete Action using UUID ##\n')
            if self.gbpcfg.gbp_action_config(0, act_uuid) == 0:
                self._log.info(
                    "\n## Step 5: Delete Action using UUID == Failed")
                return 0
            if self.gbpverify.gbp_action_verify(
                    0, act_uuid, self.act_name) != 0:
                self._log.info(
                    "\n## Step 5A: Verify Action is Deleted using -list "
                    "option == Failed")
                return 0
            if self.gbpverify.gbp_action_verify(
                    1,
                    act_uuid,
                    name=self.act_name,
                    action_type='allow',
                    shared='False') != 0:
                self._log.info(
                    "\n## Step 5B: Verify Action is Deleted using -show "
                    "option == Failed")
                return 0
            self._log.info(
                "\n## Step 5: Delete of Policy Action using UUID == Passed")
        else:
            self._log.info(
                "\n## Step 6: Recreate of Policy Action using Default "
                "== Failed")
            return 0
        if rep_cr == 0 and rep_del == 0:
            self._log.info("\n## TESTCASE_GBP_PA_FUNC_1: PASSED")
        return 1

if __name__ == '__main__':
    main()
