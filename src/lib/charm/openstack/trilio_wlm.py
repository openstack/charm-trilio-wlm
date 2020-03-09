# Copyright 2020 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections

import charmhelpers.core.hookenv as hookenv
import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip


def _get_internal_url(identity_service, service):
    ep_catalog = identity_service.relation.endpoint_checksums()
    if service in ep_catalog:
        return ep_catalog.get(service)["internal"]
    return None


@charms_openstack.adapters.adapter_property("identity-service")
def neutron_url(identity_service):
    return _get_internal_url(identity_service, "neutron")


@charms_openstack.adapters.adapter_property("identity-service")
def cinder_url(identity_service):
    return _get_internal_url(identity_service, "cinderv2")


@charms_openstack.adapters.adapter_property("identity-service")
def glance_url(identity_service):
    return _get_internal_url(identity_service, "glance")


@charms_openstack.adapters.adapter_property("identity-service")
def nova_url(identity_service):
    return _get_internal_url(identity_service, "nova")


class TrilioWLMCharm(charms_openstack.charm.HAOpenStackCharm):

    # Internal name of charm
    service_name = name = "trilio-wlm"

    workloadmgr_conf = "/etc/workloadmgr/workloadmgr.conf"
    api_paste_ini = "/etc/workloadmgr/api-paste.ini"
    alembic_ini = "/etc/workloadmgr/alembic.ini"

    # First release supported
    release = "stein"

    # List of packages to install for this charm
    # NOTE(jamespage): nova-common ensures a consistent UID is use
    # for the nova user.
    packages = ["nova-common", "workloadmgr", "python-apt"]

    # Ensure we use the right package for versioning
    version_package = "workloadmgr"

    api_ports = {
        "workloadmgr-api": {
            os_ip.PUBLIC: 8780,
            os_ip.ADMIN: 8780,
            os_ip.INTERNAL: 8780,
        }
    }

    service_type = "workloadmgr"
    default_service = "workloadmgr-api"
    services = ["wlm-api", "wlm-scheduler", "wlm-workloads"]

    required_relations = ["shared-db", "amqp", "identity-service"]

    restart_map = {
        workloadmgr_conf: services,
        api_paste_ini: ["wlm-api"],
        alembic_ini: [],
    }

    ha_resources = ["vips", "haproxy"]

    release_pkg = "workloadmgr"

    package_codenames = {
        "workloadmgr": collections.OrderedDict([("3", "stein")])
    }

    sync_cmd = [
        "alembic",
        "--config={}".format(workloadmgr_conf),
        "upgrade",
        "head",
    ]

    user = "root"
    group = "nova"

    required_services = [
        "nova",
        "neutron",
        "glance",
        "cinderv2",
        "cinderv3",
        "cinder",
    ]

    workloadmgr_install_dir = "/usr/lib/python3/dist-packages/workloadmgr"

    endpoint_template = "{}:{}/v1/$(tenant_id)s"

    def __init__(self, release=None, **kwargs):
        super().__init__(release="stein", **kwargs)

    def get_amqp_credentials(self):
        return ("triliowlm", "triliowlm")

    def get_database_setup(self):
        return [
            {
                "database": self.service_type,
                "username": self.service_type,
            }
        ]

    def configure_source(self):
        with open("/etc/apt/sources.list.d/trilio-wlm.list", "w") as tsources:
            tsources.write(hookenv.config("triliovault-pkg-source"))
        super().configure_source()

    @property
    def public_url(self):
        """Return the public endpoint URL for the default service as specified
        in the self.default_service attribute
        """
        return self.endpoint_template.format(
            os_ip.canonical_url(os_ip.PUBLIC),
            self.api_port(self.default_service, os_ip.PUBLIC),
        )

    @property
    def admin_url(self):
        """Return the admin endpoint URL for the default service as specificed
        in the self.default_service attribute
        """
        return self.endpoint_template.format(
            os_ip.canonical_url(os_ip.ADMIN),
            self.api_port(self.default_service, os_ip.ADMIN),
        )

    @property
    def internal_url(self):
        """Return the internal internal endpoint URL for the default service as
        specificated in the self.default_service attribtue
        """
        return self.endpoint_template.format(
            os_ip.canonical_url(os_ip.INTERNAL),
            self.api_port(self.default_service, os_ip.INTERNAL),
        )
