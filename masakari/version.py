# Copyright 2016 NTT DATA
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

from pbr import version as pbr_version

MASAKARI_VENDOR = "OpenStack Foundation"
MASAKARI_PRODUCT = "OpenStack Masakari"
MASAKARI_PACKAGE = None  # OS distro package version suffix

loaded = False
version_info = pbr_version.VersionInfo('masakari')
version_string = version_info.version_string


def _load_config():
    # Don't load in global context, since we can't assume
    # these modules are accessible when distutils uses
    # this module
    import configparser

    from oslo_config import cfg

    from oslo_log import log as logging

    global loaded, MASAKARI_VENDOR, MASAKARI_PRODUCT, MASAKARI_PACKAGE
    if loaded:
        return

    loaded = True

    cfgfile = cfg.CONF.find_file("release")
    if cfgfile is None:
        return

    try:
        cfg = configparser.RawConfigParser()
        cfg.read(cfgfile)

        if cfg.has_option("Masakari", "vendor"):
            MASAKARI_VENDOR = cfg.get("Masakari", "vendor")

        if cfg.has_option("Masakari", "product"):
            MASAKARI_PRODUCT = cfg.get("Masakari", "product")

        if cfg.has_option("Masakari", "package"):
            MASAKARI_PACKAGE = cfg.get("Masakari", "package")
    except Exception as ex:
        LOG = logging.getLogger(__name__)
        LOG.error("Failed to load %(cfgfile)s: %(ex)s",
                  {'cfgfile': cfgfile, 'ex': ex})


def vendor_string():
    _load_config()

    return MASAKARI_VENDOR


def product_string():
    _load_config()

    return MASAKARI_PRODUCT


def package_string():
    _load_config()

    return MASAKARI_PACKAGE


def version_string_with_package():
    if package_string() is None:
        return version_info.version_string()
    else:
        return "%s-%s" % (version_info.version_string(), package_string())
