# Noirotest Router Scripts

Make sure to run the exttrt playbooks in the playbooks directory before running the tests.

## How to run the playbook

1. Run the playbooks

````
cd playbooks
ansible-playbook -i ../hosts main.yaml 
````

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

Command parameters:

./nt_pre_setup.sh release uc_type uc_ip fab_num

````
cd noirotests

./nt_pre_setup.sh train director 10.30.120.194 202
````

3. Run test setup

````
python setup.py
````

4. Run ml2 sanity tests 

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_sanity && time python run_ml2_sanity.py 2>&1 | tee ~/ml2.log
````

5. Run gbp sanity tests

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_sanity && time python run_gbp_sanity.py 2>&1 | tee ~/gbp.log
````

6. Run east west

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_nat_func && time python test_gbp_nat_suite.py 2>&1 | tee ~/nat.log
````

7. Run north south

````
source ~/overcloudrc && export PYTHONPATH=/home/noiro/noirotest && cd ~/noirotest/testcases/testcases_dp && time python test_dp_runner.py 2>&1 | tee ~/dp.log
````


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
9. Add routes to many individual nodes instead of  -net even though they are all on same network.


## To revisit

1. Fix routes logic based on fab type (to be done in playbooks)
2. Add juju support
3. Containers and non containers logic
4. Fix routing through undercloud logic


