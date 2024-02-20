#!/usr/bin/python

import sys
import logging
import os
import datetime
import string
import re
from libs.gbp_fab_traff_libs import gbpFabTraff
from libs.gbp_pexp_traff_libs import gbpExpTraff
from libs.raise_exceptions import *


def traff_from_extgwrtr(extgwrtr_ip, fipsOftargetVMs, proto='all', jumbo=0):
    """
    Traffic from ExternalGW Router to Tenant VMs
    """
    traff = gbpFabTraff()
    targetvm_list = ['Web-Server', 'Web-Client-1',
                     'Web-Client-2', 'App-Server']
    print('FIPs of Target VMs == %s' % (fipsOftargetVMs))
    # List of FIPs ExtGWRtr will ping:
    ping_fips = [fip for x in list(fipsOftargetVMs.values()) for fip in x]
    if proto == 'all':
        if jumbo == 1:
            results_icmp = traff.test_regular_icmp(
                extgwrtr_ip, ping_fips, pkt_size='9000')
        else:
            results_icmp = traff.test_regular_icmp(extgwrtr_ip, ping_fips)
        results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
        if results_icmp != 1 and results_tcp != 1:
            return {'ICMP': list(results_icmp.keys()), 'TCP': list(results_tcp.keys())}
        elif results_icmp != 1:
            return {'ICMP': list(results_icmp.keys())}
        elif results_tcp != 1:
            return {'TCP': list(results_tcp.keys())}
        else:
            return 1
    if proto == 'icmp':
        if jumbo == 1:
            results_icmp = traff.test_regular_icmp(
                extgwrtr_ip, ping_fips, pkt_size='9000')
        else:
            results_icmp = traff.test_regular_icmp(extgwrtr_ip, ping_fips)
        if isinstance(results_icmp, dict):
            return {'ICMP': list(results_icmp.keys())}
    if proto == 'tcp':
        results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
        if isinstance(results_tcp, dict):
            return {'TCP': list(results_tcp.keys())}
