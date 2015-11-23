#!/usr/bin/env bash

# Install Pexpect & Fabric needed for running GBP Automated TestSuite
pip install pexpect
pip install fabric
pip install mailer

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/root/gbpauto"

# Change Nova-quotas as needed for running TestSuite
sed -i 's/^#quota_instances=.*/quota_instances=200/' /etc/nova/nova.conf
sed -i 's/^#quota_cores=.*/quota_cores=400/' /etc/nova/nova.conf
sed -i 's/^#quota_ram=.*/quota_ram=6400000000/' /etc/nova/nova.conf
sed -i 's/^#scheduler_max_attempts=.*/scheduler_max_attempts=1/' /etc/nova/nova.conf
systemctl restart openstack-nova-api.service
systemctl restart openstack-nova-scheduler.service
source /root/keystonerc_admin
nova quota-show

# Restart Heat-Engine & Heat-API
systemctl restart openstack-heat-engine.service
systemctl restart openstack-heat-api.service

# APIC Route-Reflector
apic route-reflector-create --ssl --no-secure --apic-ip <> --apic-username <> --apic-password <>


