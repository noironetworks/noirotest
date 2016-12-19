import sys
from aim import aim_manager
from aim.api import resource
from aim import context as aim_context

from aim import config as aim_config
from aim.db import api as db_api

class aimCrud(object):
	global aim_ctx , mgr
	aim_config.init(['--config-file', '/etc/aim/aim.conf'])
	session = db_api.get_session(expire_on_commit=True)

	aim_ctx = aim_context.AimContext(db_session=session)
	mgr = aim_manager.AimManager()
	
	def update_contract_subject(self,cont_subj,**kwargs):
		return "TBD"
 	        
