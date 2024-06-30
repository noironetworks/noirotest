# Noirotest Router Scripts

Make sure to create the router and run the exttrt playbooks in the playbooks directory before running the tests.

## Create the router

It can be done through jenkins job:

https://engci-jenkins-sjc.cisco.com/jenkins/job/team_noiro_engineering/view/Tests/job/Test%20Automation/job/new-api-router-deploy/

## How to run the playbooks

1. Run the playbooks

TODO: Create a jenkins job for it

````
cd playbooks
ansible-playbook -i ../hosts main.yaml 
````

This can also be done through jenkins job:

https://engci-jenkins-sjc.cisco.com/jenkins/job/team_noiro_engineering/view/Tests/job/Test%20Automation/job/new-api-router-setup/

2. Delete the existing external networks

````
neutron net-delete sauto_l3out-1
neutron net-delete sauto_l3out-2
````

## How to run noirotests

1. Get the code

````
https_proxy=http://proxy.esl.cisco.com:80 git clone https://github.com/noironetworks/noirotest -b new_extrtr_scripts
````

2. Run pre setup

TODO: Create a jenkins job for it

Command parameters:

./nt_pre_setup.sh release uc_type uc_ip fab_num

````
cd noirotests

./nt_pre_setup.sh train director 10.30.120.194 202
````

3. Run test setup

TODO: Create a jenkins job for it

````
python setup.py
````

4. Run ml2 sanity tests 

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_sanity && time python run_ml2_sanity.py 2>&1 | tee ~/ml2.log
````

You can also run it through jenkins job:

https://engci-jenkins-sjc.cisco.com/jenkins/job/team_noiro_engineering/view/Tests/job/Test%20Automation/job/new-noirotest-ml2-sanity


5. Run gbp sanity tests

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_sanity && time python run_gbp_sanity.py 2>&1 | tee ~/gbp.log
````

This can also be run using jenkins:

https://engci-jenkins-sjc.cisco.com/jenkins/job/team_noiro_engineering/view/Tests/job/Test%20Automation/job/new-noirotest-gbp-sanity

6. Run north south tests

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_nat_func && time python test_gbp_nat_suite.py 2>&1 | tee ~/nat.log
````

Or you can run from jenkins:

https://engci-jenkins-sjc.cisco.com/jenkins/job/team_noiro_engineering/view/Tests/job/Test%20Automation/job/new-noirotest-north-south

7. Run east west tests

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_dp && time python test_dp_runner.py 2>&1 | tee ~/dp.log
````

As others this can be run from jenkins:

https://engci-jenkins-sjc.cisco.com/jenkins/job/team_noiro_engineering/view/Tests/job/Test%20Automation/job/new-noirotest-east-west


### new_cmds_2.sh has been remaned to nt_pre_setup.sh and moved here

These features are currently disabled and will be provided elswhere.

1. Routes to external net (they are not persistant)
2. Fab interface name logic (Why is it needed)
3. Fab6 and fab8 logic
4. Juju support
5. Package installation
6. /etc/hosts setup
7. Containers and non-containers logic
8. Routing to overcloud through undercloud (Assumes (incorrecty) extrtr and undercloud are l2 adjecent) 
9. It adds routes to many individual nodes instead of  -net even though they are all on same subnet.


## To revisit

1. Fix routes logic based on fab type (to be done in setup playbooks)
2. Add juju support
3. Containers and non containers logic
4. Fix routing through undercloud logic
5. Delete extrnal net at the beginning of all noirotests
6. Use VMs with smaller footprint
7. Cleanup should not delete all networks (e.g. LB Net for octavia)
8. ssh filter at many places, simplify


