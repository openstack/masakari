# Copyright (c) 2016 NTT DATA
# All Rights Reserved.
#
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

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

nova_opts = [
    cfg.StrOpt('nova_catalog_admin_info',
               default='compute:nova:publicURL',
               help='Match this value when searching for nova in the '
                    'service catalog. Format is: separated values of '
                    'the form: '
                    '<service_type>:<service_name>:<endpoint_type>'),
    cfg.StrOpt('os_region_name',
               help='Region name of this node'),
    cfg.StrOpt('nova_ca_certificates_file',
               help='Location of ca certificates file to use for nova client '
                    'requests.'),
    cfg.BoolOpt('nova_api_insecure',
                default=False,
                help='Allow to perform insecure SSL requests to nova'),
    cfg.StrOpt('os_privileged_user_name',
               help='OpenStack privileged account username. Used for requests '
                    'to other services (such as Nova) that require an account '
                    'with special rights.'),
    cfg.StrOpt('os_privileged_user_password',
               help='Password associated with the OpenStack privileged '
                    'account.',
               secret=True),
    cfg.StrOpt('os_privileged_user_tenant',
               help='Tenant name associated with the OpenStack privileged '
                    'account.'),
    cfg.URIOpt('os_privileged_user_auth_url',
               help='Auth URL associated with the OpenStack privileged '
                    'account.'),
    cfg.StrOpt('os_user_domain_name',
               default="default",
               help='User domain name associated with the OpenStack '
                    'privileged account.'),
    cfg.StrOpt('os_project_domain_name',
               default="default",
               help='Project domain name associated with the OpenStack '
                    'privileged account.'),
    cfg.StrOpt('os_system_scope',
               help='Scope for system operations.'),
]


def register_opts(conf):
    conf.register_opts(nova_opts)
    ks_loading.register_session_conf_options(conf, 'DEFAULT')


def list_opts():
    return {
        'DEFAULT': nova_opts
    }
