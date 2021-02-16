import sys
from aim import aim_manager
from aim.api import resource
from aim import context as aim_context

from aim import config as aim_config
from aim.db import api as db_api

class aimcrud(object):
    global tnt
    tnt = 'common'

    def act_filter(self,action):
        try:
             if action == 'create':
                 mgr.create(aim_ctx,resource.Filter(tenant_name=tnt,
                            name='noiro-ssh'))
             if action == 'delete':
                 mgr.delete(aim_ctx,resource.Filter(tenant_name=tnt,
                            name='noiro-ssh'))

        except Exception as e:
            print('\nnoiro-ssh filter-create failed: '+repr(e))
            return 0

    def act_filter_entry(self,action):
        try:
             if action == 'create':
                 mgr.create(aim_ctx,resource.FilterEntry(
                        tenant_name=tnt, filter_name='noiro-ssh',
                        name='ssh', ether_type='ip', ip_protocol='tcp',
                        source_from_port=22, source_to_port=22))
                 mgr.create(aim_ctx,resource.FilterEntry(
                        tenant_name=tnt, filter_name='noiro-ssh',
                        name='rev-ssh',ether_type='ip', ip_protocol='tcp',
                        dest_from_port=22,dest_to_port=22))
             if action == 'delete':
                 for name in ['ssh','rev-ssh']:
                     mgr.delete(aim_ctx,resource.FilterEntry(
                                tenant_name=tnt, filter_name='noiro-ssh',
                                name=name))
        except Exception as e:
            print('\n Filter-Entry ssh %s failed: ' %(action)+repr(e))
            return 0

    def act_svc_contract_subject(self,action):
        try:
            for cs in mgr.find(aim_ctx,resource.ContractSubject):
                if 'Svc' in cs.name:
                    csfltrs = cs.__dict__['bi_filters']
                    if action == 'create': #add filter to svc-ctc-subj
                        csfltrs.append('noiro-ssh')
                        mgr.update(aim_ctx,cs,bi_filters=csfltrs)
                    if action == 'delete': #del filter to svc-ctc-subj
                        csfltrs.remove('noiro-ssh')
                        mgr.update(aim_ctx,cs,bi_filters=csfltrs)
        except Exception as e:
            print('\nUpdate of svc-ctc failed: '+repr(e))
            return 0

## Get Global instances/variables
action = sys.argv[1]
aim_config.init(['--config-file', '/etc/aim/aim.conf'])
session = db_api.get_session(expire_on_commit=True)
aim_ctx = aim_context.AimContext(db_session=session)
mgr = aim_manager.AimManager()

## Instantiate crud class
crud = aimcrud()
if action == 'create':
    # Create a filter
    print("\nCreating the Filter noiro-ssh")
    crud.act_filter(action)
    # Create filter-entries
    print("\nCreating Filter-entries ssh & rev-ssh")
    crud.act_filter_entry(action)
    # Add the noiro-ssh filter to Svc Contract Subject
    print("\nAdding the noiro-ssh filter to Svc Contract Subject")
    crud.act_svc_contract_subject(action)

if action == 'delete':
    # Remove the noiro-ssh filter to Svc Contract Subject
    print("\nRemoving the noiro-ssh filter from Svc Contract Subject")
    crud.act_svc_contract_subject(action)
    # Delete filter-entries
    print("\nDeleting Filter-entries ssh & rev-ssh")
    crud.act_filter_entry(action)
    # Delete filter
    print("\nDeleting the Filter noiro-ssh")
    crud.act_filter(action)

