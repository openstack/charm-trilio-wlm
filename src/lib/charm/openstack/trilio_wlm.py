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
import copy
import subprocess

import charmhelpers.core.hookenv as hookenv
import charmhelpers.contrib.openstack.utils as os_utils

import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.plugins
import charms_openstack.ip as os_ip

import charms.reactive as reactive

charms_openstack.plugins.trilio.make_trilio_handlers()


def _get_internal_url(identity_service, service):
    ep_catalog = identity_service.relation.endpoint_checksums()
    if service in ep_catalog:
        return ep_catalog.get(service)["internal"]
    return None


@charms_openstack.adapters.config_property
def translated_backup_target_type(cls):
    _type = hookenv.config("backup-target-type").lower()
    if _type == "experimental-s3":
        return 's3'
    return _type


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


class TrilioWLMDatabaseAdapter(
        charms_openstack.adapters.DatabaseRelationAdapter):
    """
    Overrides default class to force use of the mysqldb driver
    """

    @property
    def driver(self):
        return "mysql"


class TrilioWLMCharmRelationAdapters(
        charms_openstack.adapters.OpenStackAPIRelationAdapters):
    """
    Adapters collection to append specific adapters for TrilioWLM
    """
    relation_adapters = {
        'amqp': charms_openstack.adapters.RabbitMQRelationAdapter,
        'shared_db': TrilioWLMDatabaseAdapter,
        'cluster': charms_openstack.adapters.PeerHARelationAdapter,
        'coordinator_memcached': (
            charms_openstack.adapters.MemcacheRelationAdapter
        ),
    }


class TrilioWLMCharm(charms_openstack.plugins.TrilioVaultCharm,
                     charms_openstack.plugins.TrilioVaultCharmGhostAction):

    # Internal name of charm
    service_name = name = "trilio-wlm"

    adapters_class = TrilioWLMCharmRelationAdapters

    workloadmgr_conf = "/etc/workloadmgr/workloadmgr.conf"
    api_paste_ini = "/etc/workloadmgr/api-paste.ini"
    alembic_ini = "/etc/workloadmgr/alembic.ini"
    object_store_conf = "/etc/tvault-object-store/tvault-object-store.conf"

    release = "stein"
    trilio_release = "4.0"

    base_packages = [
        "linux-image-virtual",  # Used for libguestfs supermin appliance
        "nova-common",
        "workloadmgr",
        "python3-workloadmgrclient",
        "python3-contegoclient",
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
        ),
        "nova-common": os_utils.PACKAGE_CODENAMES["nova-common"],
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

    os_release_pkg = 'nova-common'

    workloadmgr_install_dir = "/usr/lib/python3/dist-packages/workloadmgr"

    endpoint_template = "{}/v1/$(tenant_id)s"

    def __init__(self, release=None, **kwargs):
        super().__init__(release="stein", **kwargs)

    @property
    def backup_target_type(self):
        # The main purpose of this property is to translate experimental-s3
        # to s3 and s3 to UNKNOWN. This forces the deployer to
        # use 'experimental-s3' for s3 support but the code can stay clean and
        # refer to s3.
        _type = hookenv.config("backup-target-type").lower()
        if _type == 'experimental-s3':
            return 's3'
        if _type == 'nfs':
            return 'nfs'
        return 'UNKNOWN'

    # List of packages to install for this charm
    # NOTE(jamespage): nova-common ensures a consistent UID is use
    # for the nova user.
    @property
    def packages(self):
        _pkgs = copy.deepcopy(self.base_packages)
        if self.backup_target_type == 's3':
            _pkgs.append('python3-s3-fuse-plugin')
        return _pkgs

    def get_amqp_credentials(self):
        return ("triliowlm", "triliowlm")

    def get_database_setup(self):
        return [{"database": self.service_type, "username": self.service_type}]

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
        _svcs = ["wlm-api", "wlm-scheduler", "wlm-workloads"]
        if not reactive.flags.is_flag_set("ha.available"):
            # Only manage wlm-cron service when running solo as an
            # instance across the cluster which will be managed by
            # corosync and pacemaker
            _svcs.append("wlm-cron")
        if self.backup_target_type == 's3':
            _svcs.append('tvault-object-store')
        return _svcs

    @property
    def restart_map(self):
        """Generate the restart map for this service
        """
        _restart_map = {
            self.workloadmgr_conf: self.services,
            self.api_paste_ini: ["wlm-api"],
            self.alembic_ini: [],
        }
        if self.backup_target_type == 's3':
            _restart_map[self.object_store_conf] = ['tvault-object-store']
            _restart_map[
                charms_openstack.plugins.trilio.S3_SSL_CERT_FILE] = [
                    'tvault-object-store']
        return _restart_map

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
        if not hookenv.is_leader():
            raise charms_openstack.plugins.classes.UnitNotLeaderException(
                "please run on leader unit")
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
                "--os-user-domain-name",
                "admin_domain",
                "--os-project-domain-id",
                identity_service.admin_domain_id(),
                "--os-project-id",
                identity_service.admin_project_id(),
                "--os-project-name",
                "admin",
                "--os-region-name",
                hookenv.config("region"),
                "trust-create",
                "--is_cloud_trust",
                "True",
                "Admin",
            ]
        )
        hookenv.leader_set({"trusted": True})

    def create_license(self, identity_service):
        if not hookenv.is_leader():
            raise charms_openstack.plugins.classes.UnitNotLeaderException(
                "please run on leader unit")
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
                "--os-user-domain-name",
                "service_domain",
                "--os-project-domain-id",
                identity_service.service_domain_id(),
                "--os-project-id",
                identity_service.service_tenant_id(),
                "--os-project-name",
                identity_service.service_tenant(),
                "--os-region-name",
                hookenv.config("region"),
                "license-create",
                license_file,
            ]
        )
        hookenv.leader_set({"licensed": True})

    @property
    def licensed(self):
        return hookenv.leader_get("licensed")

    @property
    def trusted(self):
        return hookenv.leader_get("trusted")

    def custom_assess_status_check(self):
        """Check required configuration options are set"""
        check_config_set = []
        if self.backup_target_type == "nfs":
            check_config_set = ['nfs-shares']
        elif self.backup_target_type == "s3":
            check_config_set = [
                "tv-s3-secret-key",
                "tv-s3-access-key",
                "tv-s3-region-name",
                "tv-s3-bucket",
                "tv-s3-endpoint-url"]
        unset_config = [c for c in check_config_set if not hookenv.config(c)]
        if unset_config:
            return "blocked", "{} configuration not set".format(
                ', '.join(unset_config))
        # For s3 support backup-target-type should be set to 'experimental-s3'
        # as s3 support is pre-production. The self.backup_target_type
        # property will do any transaltion needed.
        if self.backup_target_type not in ["nfs", "s3"]:
            return "blocked", "Backup target type not supported"
        return None, None

    def custom_assess_status_last_check(self):
        """Check required configuration options are set"""
        if not self.trusted:
            return (
                "blocked",
                "application not trusted; please run "
                "'create-cloud-admin-trust' action",
            )
        if not self.licensed:
            return (
                "blocked",
                "application not licensed; please run 'create-license' action",
            )
        return None, None

    @classmethod
    def trilio_version_package(cls):
        return 'workloadmgr'


class TrilioWLMCharmUssuri40(TrilioWLMCharm):

    # First release supported
    release = "ussuri"
    trilio_release = "4.0"
    python_version = 3

    base_packages = [
        "linux-image-virtual",  # Used for libguestfs supermin appliance
        "nova-common",
        "workloadmgr",
        "python3-workloadmgrclient",
        "python3-contegoclient",
        "python3-glanceclient",
        "python3-neutronclient",
        "python3-apt",
        "python3-retrying",
    ]


class TrilioWLMCharmUssuri41(TrilioWLMCharmUssuri40):

    # First release supported
    release = "ussuri"
    trilio_release = "4.1"
