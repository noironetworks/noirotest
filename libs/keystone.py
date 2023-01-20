#from keystoneclient.v2_0 import client as kc
from keystoneclient.v3 import client as kc

class Keystone(object):
    def __init__(self, ostack_controller, username='admin',
                 password='noir0123', tenant_name='admin'):
        cred = {}
        cred['username'] = username
        cred['password'] = password
        cred['tenant_name'] = tenant_name
        #cred['auth_url'] = "http://%s:5000/v2.0/" % ostack_controller
        cred['auth_plugin'] = 'v3password'
        cred['auth_url'] = 'http://%s:35357/v3' % ostack_controller
        cred['user_domain_name'] = 'default'
        cred['project_domain_name'] = 'default'
        cred['project_name'] = tenant_name

        self.client = kc.Client(**cred)

    def get_token(self):
        return self.client.service_catalog.get_token()['id']

    def get_tenant_list(self,obj=False):
        """ 
        Returns list of tenants as a dict of ID & Name
        obj:: if set to True, then it will return of list
        tenant objects
        """
        if obj:
            return self.client.projects.list()
        else:
            tntnameID = {}
            tntlist = self.client.projects.list()
            for tnt in tntlist:
                tntnameID[tnt.name.encode()]=tnt.id.encode()
            return tntnameID    

    def get_tenant(self, tenant_name):
        tntlist = self.client.projects.list()
        for tnt in tntlist:
            if tnt.name == tenant_name:
               return tnt

    def get_tenant_attribute(self, tenant_name, attribute):
        tntlist = self.get_tenant_list(obj=True)
        for tnt in tntlist:
            if tnt.name == tenant_name:
                return tnt.__getattribute__(attribute).encode()

    def create_tenant(self, tenant_name, enabled=True):
        if self.tenant_exists(tenant_name):
            return
        try:
            return self.client.projects.create(project_name=tenant_name,
                                           enabled=enabled)
        except:
            return None
        
    def get_users_list(self):
        """ returns list of users """
        return self.client.users.list()

    def get_user(self, user_name):
        ret = None
        rl = self.get_users_list()
        for r in rl:
            if r.name == user_name:
                return r
        return ret

    def get_user_attribute(self, user_name, attribute):
        ret = None
        rl = self.get_users_list()
        for r in rl:
            if r.name == user_name:
                ret = r.__getattribute__(attribute)
                break
        return ret

    def user_exists(self, user_name):
        rl = self.get_users_list()
        for r in rl:
            if r.name == user_name:
                return True
        return False

    def get_role_list(self):
        return self.client.roles.list()

    def get_role_attribute(self, role, attribute):
        ret = None
        rl = self.get_role_list()
        for r in rl:
            if r.name == role:
                ret = r.__getattribute__(attribute)
                break
        return ret

    def setup_demo(self):
        self.create_tenant(tenant_name='HR')
        self.create_tenant(tenant_name='Engineering')
        hr_id = self.get_tenant_attribute(tenant_name='HR', attribute='id')
        eng_id = self.get_tenant_attribute(tenant_name='Engineering', attribute='id')

        demo_user_id = self.get_user_attribute('admin', 'id')
        admin_user_id = self.get_user_attribute('demo', 'id')
        neutron_user_id = self.get_user_attribute('neutron', 'id')

        hstack_owner_role_id = self.get_role_attribute('heat_stack_owner', 'id')
        member_role_id = self.get_role_attribute('_member_', 'id')

        self.client.roles.add_user_role(user=demo_user_id, role=hstack_owner_role_id, project=hr_id)
        self.client.roles.add_user_role(user=demo_user_id, role=member_role_id, project=hr_id)
        self.client.roles.add_user_role(user=demo_user_id, role=hstack_owner_role_id, project=eng_id)
        self.client.roles.add_user_role(user=demo_user_id, role=member_role_id, project=eng_id)

        self.client.roles.add_user_role(user=admin_user_id, role=hstack_owner_role_id, project=hr_id)
        self.client.roles.add_user_role(user=admin_user_id, role=member_role_id, project=hr_id)
        self.client.roles.add_user_role(user=admin_user_id, role=hstack_owner_role_id, project=eng_id)
        self.client.roles.add_user_role(user=admin_user_id, role=member_role_id, project=eng_id)

        self.client.roles.add_user_role(user=neutron_user_id, role=hstack_owner_role_id, project=hr_id)
        self.client.roles.add_user_role(user=neutron_user_id, role=member_role_id, project=hr_id)
        self.client.roles.add_user_role(user=neutron_user_id, role=hstack_owner_role_id, project=eng_id)
        self.client.roles.add_user_role(user=neutron_user_id, role=member_role_id, project=eng_id)


