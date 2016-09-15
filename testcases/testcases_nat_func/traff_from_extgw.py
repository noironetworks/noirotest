#!/usr/bin/python

import sys
import logging
import os
import datetime
import string
import re
from time import sleep
from libs.gbp_fab_traff_libs import Gbp_def_traff
from libs.gbp_pexp_traff_libs import Gbp_pexp_traff
from libs.raise_exceptions import *


def traff_from_extgwrtr(extgwrtr_ip, fipsOftargetVMs, proto='all', jumbo=0):
    """
    Traffic from ExternalGW Router to Tenant VMs
    """
    traff = Gbp_def_traff()
    print 'FIPs of Target VMs == %s' % (fipsOftargetVMs)
    # List of FIPs ExtGWRtr will ping, ping_fips should be type List
    if isinstance(fipsOftargetVMs,dict):
        ping_fips = fipsOftargetVMs.values() 
    if isinstance(fipsOftargetVMs,list):
        ping_fips = fipsOftargetVMs
    if not isinstance(fipsOftargetVMs,list):
        ping_fips = [fipsOftargetVMs]
    attemptall = 1
    if proto == 'all':
        while attemptall < 4:
            if jumbo == 1:
                results_icmp = traff.test_regular_icmp(
                extgwrtr_ip, ping_fips, pkt_size='9000')
            else:
                results_icmp = traff.test_regular_icmp(extgwrtr_ip, ping_fips)
            results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
            if results_icmp != 1 and results_tcp != 1:
                retval = {'ICMP': results_icmp.keys(), 'TCP': results_tcp.keys()}
            elif results_icmp != 1:
                retval = {'ICMP': results_icmp.keys()}
            elif results_tcp != 1:
                retval = {'TCP': results_tcp.keys()}
            else:
                return 1
            if isinstance(retval,dict):
               print "Wait for 10 secs before the next ICMP & TCP retry\n"
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
        while attempt < 4:
            if isinstance(results_icmp, dict):
               print "Wait for 10 secs before the next ICMP retry\n"
               sleep(10)
               results_icmp = traff.test_regular_icmp(extgwrtr_ip, ping_fips)
               attempt += 1
            else:
               break
        if attempt == 4:
               return {'ICMP': results_icmp.keys()}
    if proto == 'tcp':
        results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
        retry = 1
        while retry < 4:
            if isinstance(results_tcp, dict):
               print "Wait for 10 secs before the next TCP retry\n"
               sleep(10)
               results_tcp = traff.test_regular_tcp(extgwrtr_ip, ping_fips)
               retry += 1
            else:
               break
        if retry == 4:
            return {'TCP': results_tcp.keys()}
