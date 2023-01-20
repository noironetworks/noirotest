#!/usr/bin/python

import sys
import logging
import os
import datetime
import string
import re
from time import sleep
from libs.gbp_fab_traff_libs import gbpFabTraff
from libs.gbp_pexp_traff_libs import gbpExpTraff
from libs.raise_exceptions import *
from testcases.config import conf


max_traff_attempts = conf.get('traffic_attempts', 10)
def traff_from_extgwrtr(extgwrtr_ip, fipsOftargetVMs, proto='all', jumbo=0):
    """
    Traffic from ExternalGW Router to Tenant VMs
    """
    traff = gbpFabTraff()
    print('FIPs of Target VMs == %s' % (fipsOftargetVMs))
    # List of FIPs ExtGWRtr will ping, ping_fips should be type List
    if isinstance(fipsOftargetVMs,dict):
        ping_fips = list(fipsOftargetVMs.values()) 
    if isinstance(fipsOftargetVMs,list):
        ping_fips = fipsOftargetVMs
    if not isinstance(fipsOftargetVMs,list):
        ping_fips = [fipsOftargetVMs]
    attemptall = 1
    if proto == 'all':
        while attemptall < max_traff_attempts:
            if jumbo == 1:
                results_icmp = traff.test_regular_icmp(
                extgwrtr_ip, ping_fips, pkt_size='9000')
            else:
                results_icmp = traff.test_regular_icmp(extgwrtr_ip, ping_fips)
            results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
            if results_icmp != 1 and results_tcp != 1:
                retval = {'ICMP': list(results_icmp.keys()), 'TCP': list(results_tcp.keys())}
            elif results_icmp != 1:
                retval = {'ICMP': list(results_icmp.keys())}
            elif results_tcp != 1:
                retval = {'TCP': list(results_tcp.keys())}
            else:
                return 1
            if isinstance(retval,dict):
               print("Wait for 10 secs before the next ICMP & TCP retry\n")
               sleep(10)
               attemptall += 1
        return retval
    if proto == 'icmp':
        if jumbo == 1:
            results_icmp = traff.test_regular_icmp(
                extgwrtr_ip, ping_fips, pkt_size='9000')
        else:
            results_icmp = traff.test_regular_icmp(extgwrtr_ip, ping_fips)
        attempt = 1
        while attempt < max_traff_attempts:
            if isinstance(results_icmp, dict):
               print("Wait for 10 secs before the next ICMP retry\n")
               sleep(10)
               results_icmp = traff.test_regular_icmp(extgwrtr_ip, ping_fips)
               attempt += 1
            else:
               break
        if attempt == max_traff_attempts:
               return {'ICMP': list(results_icmp.keys())}
    if proto == 'tcp':
        results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
        retry = 1
        while retry < max_traff_attempts:
            if isinstance(results_tcp, dict):
               print("Wait for 10 secs before the next TCP retry\n")
               sleep(10)
               results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
               retry += 1
            else:
               break
        if retry == max_traff_attempts:
            return {'TCP': list(results_tcp.keys())}
