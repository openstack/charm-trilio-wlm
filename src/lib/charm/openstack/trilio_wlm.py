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

import base64
import collections
import subprocess
import os

import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as host

import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip

import charms.reactive as reactive

TV_MOUNTS = "/var/triliovault-mounts"


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


class IdentityServiceIncompleteException(Exception):
    """Signal that the identity-service relation is not complete"""

    pass


class LicenseFileMissingException(Exception):
    """Signal that the license file has not been provided as a resource"""

    pass


class NFSShareNotMountedException(Exception):
    """Signal that the trilio nfs share is not mount"""

    pass


class GhostShareAlreadyMountedException(Exception):
    """Signal that a ghost share is already mounted"""

    pass


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
    packages = [
        "linux-image-virtual",  # Used for libguestfs supermin appliance
        "nova-common",
        "workloadmgr",
        "python-apt",
    ]

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

    required_relations = ["shared-db", "amqp", "identity-service"]

    ha_resources = ["vips", "haproxy"]

    release_pkg = "workloadmgr"

    package_codenames = {
        "workloadmgr": collections.OrderedDict(
            [("3", "stein"), ("4", "train")]
        )
    }

    sync_cmd = [
        "alembic",
        "--config={}".format(alembic_ini),
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

    endpoint_template = "{}/v1/$(tenant_id)s"

    def __init__(self, release=None, **kwargs):
        super().__init__(release="stein", **kwargs)

    def get_amqp_credentials(self):
        return ("triliowlm", "triliowlm")

    def get_database_setup(self):
        return [{"database": self.service_type, "username": self.service_type}]

    def configure_source(self):
        with open("/etc/apt/sources.list.d/trilio-wlm.list", "w") as tsources:
            tsources.write(hookenv.config("triliovault-pkg-source"))
        super().configure_source()

    @property
    def public_url(self):
        """Return the public endpoint URL for the default service as specified
        in the self.default_service attribute
        """
        return self.endpoint_template.format(super().public_url)

    @property
    def admin_url(self):
        """Return the admin endpoint URL for the default service as specificed
        in the self.default_service attribute
        """
        return self.endpoint_template.format(super().admin_url)

    @property
    def internal_url(self):
        """Return the internal internal endpoint URL for the default service as
        specificated in the self.default_service attribtue
        """
        return self.endpoint_template.format(super().internal_url)

    @property
    def services(self):
        """Determine the services associated with this class
        """
        if reactive.flags.is_flag_set("ha.available"):
            # Stop managing wlm-cron service as it needs to be single
            # instance across the cluster which will be managed by
            # corosync and pacemaker
            return ["wlm-api", "wlm-scheduler", "wlm-workloads"]
        return ["wlm-api", "wlm-scheduler", "wlm-workloads", "wlm-cron"]

    @property
    def restart_map(self):
        """Generate the restart map for this service
        """
        return {
            self.workloadmgr_conf: self.services,
            self.api_paste_ini: ["wlm-api"],
            self.alembic_ini: [],
        }

    def configure_ha_resources(self, hacluster):
        """Inform the ha subordinate about each service it should manage.

        Delegate core resources to the parent class and add wlm-cron as
        and additional init service to manage

        @param hacluster instance of interface class HAClusterRequires
        """
        super().configure_ha_resources(hacluster)
        hacluster.add_systemd_service(self.name, "wlm-cron", clone=False)

    def create_trust(self, identity_service, cloud_admin_password):
        """Create trust between Trilio WLM service user and Cloud Admin
        """
        if not identity_service.base_data_complete():
            raise IdentityServiceIncompleteException(
                "identity-service relation incomplete"
            )
        # NOTE(jamespage): hardcode of admin username here may be brittle
        subprocess.check_call(
            [
                "workloadmgr",
                "--os-username",
                "admin",
                "--os-password",
                cloud_admin_password,
                "--os-auth-url",
                "{}://{}:{}/v3".format(
                    identity_service.service_protocol(),
                    identity_service.service_host(),
                    identity_service.service_port(),
                ),
                "--os-domain-id",
                identity_service.admin_domain_id(),
                "--os-tenant-id",
                identity_service.admin_project_id(),
                "--os-tenant-name",
                "admin",
                "--os-region-name",
                hookenv.config("region"),
                "trust-create",
                "--is_cloud_trust",
                "True",
                "Admin",
            ]
        )

    def create_license(self, identity_service):
        license_file = hookenv.resource_get("license")
        if not license_file:
            raise LicenseFileMissingException(
                "License file not provided as a resource"
            )
        if not identity_service.base_data_complete():
            raise IdentityServiceIncompleteException(
                "identity-service relation incomplete"
            )
        subprocess.check_call(
            [
                "workloadmgr",
                "--os-username",
                identity_service.service_username(),
                "--os-password",
                identity_service.service_password(),
                "--os-auth-url",
                "{}://{}:{}/v3".format(
                    identity_service.service_protocol(),
                    identity_service.service_host(),
                    identity_service.service_port(),
                ),
                "--os-domain-id",
                identity_service.service_domain_id(),
                "--os-tenant-id",
                identity_service.service_tenant_id(),
                "--os-tenant-name",
                identity_service.service_tenant(),
                "--os-region-name",
                hookenv.config("region"),
                "license-create",
                license_file,
            ]
        )

    def _encode_endpoint(self, backup_endpoint):
        """base64 encode an backup endpoint for cross mounting support"""
        return base64.b64encode(backup_endpoint.encode()).decode()

    def ghost_nfs_share(self, ghost_share):
        """Bind mount the local units nfs share to another sites location

        :param ghost_share: NFS share URL to ghost
        :type ghost_share: str
        """
        nfs_share_path = os.path.join(
            TV_MOUNTS, self._encode_endpoint(hookenv.config("nfs-shares"))
        )
        ghost_share_path = os.path.join(
            TV_MOUNTS, self._encode_endpoint(ghost_share)
        )

        if not os.path.exists(ghost_share_path):
            os.mkdir(ghost_share_path)

        current_mounts = [mount[0] for mount in host.mounts()]

        if nfs_share_path not in current_mounts:
            # Trilio has not mounted the NFS share so return
            raise NFSShareNotMountedException(
                "nfs-shares ({}) not mounted".format(
                    hookenv.config("nfs-shares")
                )
            )

        if ghost_share_path in current_mounts:
            # bind mount already setup so return
            raise GhostShareAlreadyMountedException(
                "ghost mountpoint ({}) already bound".format(ghost_share_path)
            )

        host.mount(nfs_share_path, ghost_share_path, options="bind")
