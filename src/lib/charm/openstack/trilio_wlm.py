import collections
import subprocess
import pathlib

import charmhelpers.core.hookenv as hookenv
import charms_openstack.charm
import charms_openstack.ip as os_ip


class TrilioWLMCharm(charms_openstack.charm.HAOpenStackCharm):

    # Internal name of charm
    service_name = name = "trilio-wlm"

    workloadmgr_conf = "/etc/workloadmgr/workloadmgr.conf"
    api_paste_ini = "/etc/workloadmgr/api-paste.ini"

    # First release supported
    release = "stein"

    # List of packages to install for this charm
    packages = ["workloadmgr", "python-apt"]

    api_ports = {
        "workloadmgr-api": {os_ip.PUBLIC: 8780, os_ip.ADMIN: 8780, os_ip.INTERNAL: 8780}
    }

    service_type = "workloadmgr"
    default_service = "workloadmgr-api"
    services = ["wlm-api", "wlm-scheduler", "wlm-workloads"]

    required_relations = ["shared-db", "amqp", "identity-service"]

    restart_map = {workloadmgr_conf: services, api_paste_ini: ["wlm-api"]}

    ha_resources = ["vips", "haproxy"]

    release_pkg = "workloadmgr"

    package_codenames = {"workloadmgr": collections.OrderedDict([("3", "stein")])}

    sync_cmd = ["alembic", "--config={}".format(workloadmgr_conf), "upgrade", "head"]

    user = "root"
    group = "nova"

    required_services = ["nova", "neutron", "glance", "cinderv2", "cinderv3", "cinder"]

    workloadmgr_install_dir = "/usr/lib/python3/dist-packages/workloadmgr"

    def __init__(self, release=None, **kwargs):
        super().__init__(release="stein", **kwargs)

    def get_amqp_credentials(self):
        return ("triliowlm", "triliowlm")

    def get_database_setup(self):
        return [
            {
                "database": self.service_type,
                "username": self.service_type,
                "hostname": hookenv.network_get_primary_address("shared-db"),
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
        return "{}:{}/v1/$(tenant_id)s".format(
            os_ip.canonical_url(os_ip.PUBLIC),
            self.api_port(self.default_service, os_ip.PUBLIC),
        )

    @property
    def admin_url(self):
        """Return the admin endpoint URL for the default service as specificed
        in the self.default_service attribute
        """
        return "{}:{}/v1/$(tenant_id)s".format(
            os_ip.canonical_url(os_ip.ADMIN),
            self.api_port(self.default_service, os_ip.ADMIN),
        )

    @property
    def internal_url(self):
        """Return the internal internal endpoint URL for the default service as
        specificated in the self.default_service attribtue
        """
        return "{}:{}/v1/$(tenant_id)s".format(
            os_ip.canonical_url(os_ip.INTERNAL),
            self.api_port(self.default_service, os_ip.INTERNAL),
        )
