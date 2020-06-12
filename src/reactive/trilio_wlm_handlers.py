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

import charms_openstack.charm as charm
import charms.reactive as reactive

# This charm's library contains all of the handler code for this charm
import charm.openstack.trilio_wlm as trilio_wlm  # noqa

charm.use_defaults(
    "charm.installed",
    "amqp.connected",
    "shared-db.connected",
    "identity-service.connected",
    "identity-service.available",  # enables SSL support
    "config.changed",
    "update-status",
    "certificates.available",
    "cluster.available",
)


@reactive.when("shared-db.available")
@reactive.when("identity-service.available")
@reactive.when("amqp.available")
def render_config(*args):
    """Render the configuration for charm when all the interfaces are
    available.
    """
    with charm.provide_charm_instance() as charm_class:
        charm_class.upgrade_if_available(args)
        charm_class.render_with_interfaces(args)
        charm_class.assess_status()
    reactive.set_state("config.rendered")


@reactive.when("config.rendered")
def init_db():
    with charm.provide_charm_instance() as charm_class:
        charm_class.db_sync()


@reactive.when("ha.connected")
def cluster_connected(hacluster):
    """Configure HA resources in corosync"""
    with charm.provide_charm_instance() as charm_class:
        charm_class.configure_ha_resources(hacluster)
        charm_class.assess_status()


@reactive.when("identity-service.connected")
def request_endpoint_notification(identity_service):
    """Request notification about endpoint changes"""
    with charm.provide_charm_instance() as charm_class:
        identity_service.request_notification(charm_class.required_services)


@reactive.when_any("config.changed.triliovault-pkg-source",
                   "config.changed.openstack-origin")
def install_source_changed():
    """Trigger re-install of charm if source configuration options change"""
    reactive.clear_flag("charm.installed")
    reactive.set_flag("upgrade.triliovault")
