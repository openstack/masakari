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
    cfg.StrOpt('nova_catalog_info',
               default='compute:Compute Service:publicURL',
               help='Match this value when searching for nova in the '
                    'service catalog. Format is: separated values of '
                    'the form: '
                    '<service_type>:<service_name>:<endpoint_type>'),
    cfg.StrOpt('nova_catalog_admin_info',
               default='compute:Compute Service:adminURL',
               help='Same as nova_catalog_info, but for admin endpoint.'),
    cfg.StrOpt('nova_endpoint_template',
               help='Override service catalog lookup with template for nova '
                    'endpoint e.g. http://localhost:8774/v2/%(project_id)s'),
    cfg.StrOpt('nova_endpoint_admin_template',
               help='Same as nova_endpoint_template, but for admin endpoint.'),
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
]


def register_opts(conf):
    conf.register_opts(nova_opts)
    ks_loading.register_session_conf_options(conf, 'DEFAULT')


def list_opts():
    return {
        'DEFAULT': nova_opts
    }
