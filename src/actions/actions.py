#!/usr/local/sbin/charm-env python3
# Copyright 2018,2020 Canonical Ltd
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

import os
import sys

# Load modules from $CHARM_DIR/lib
sys.path.append("lib")

from charms.layer import basic

basic.bootstrap_charm_deps()
basic.init_config_states()

import charmhelpers.core.hookenv as hookenv

import charms.reactive as reactive

import charms_openstack.charm

# import the trilio_wlm module to get the charm definitions created.
import charm.openstack.trilio_wlm  # noqa


def create_cloud_admin_trust(*args):
    """Create trust relation between Trilio WLM and Cloud Admin
    """
    cloud_admin_password = hookenv.action_get("password")
    identity_service = reactive.endpoint_from_name(
        "identity-service"
    )
    with charms_openstack.charm.provide_charm_instance() as trilio_wlm_charm:
        trilio_wlm_charm.create_trust(identity_service, cloud_admin_password)
        trilio_wlm_charm._assess_status()


def create_license(*args):
    """Create license for operation of TrilioVault
    """
    identity_service = reactive.endpoint_from_name(
        "identity-service"
    )
    with charms_openstack.charm.provide_charm_instance() as trilio_wlm_charm:
        trilio_wlm_charm.create_license(identity_service)
        trilio_wlm_charm._assess_status()


def ghost_share(*args):
    """Ghost mount secondard TV deployment nfs-share
    """
    secondary_nfs_share = hookenv.action_get("nfs-shares")
    with charms_openstack.charm.provide_charm_instance() as trilio_wlm_charm:
        trilio_wlm_charm.ghost_nfs_share(secondary_nfs_share)
        trilio_wlm_charm._assess_status()


def update_trilio(*args):
    """Run setup after Trilio upgrade.
    """
    with charms_openstack.charm.provide_charm_instance() as trilio_wlm_charm:
        interfaces = ["shared-db", "amqp"]
        endpoints = [
            reactive.relations.endpoint_from_flag("{}.available".format(i))
            for i in interfaces]
        # identity-service is of type reactive.Endpoint rather than
        # reactive.RelationBase and needs a different method to instantiate it.
        endpoints.append(reactive.endpoint_from_name("identity-service"))
        trilio_wlm_charm.run_trilio_upgrade(endpoints)
        trilio_wlm_charm._assess_status()


# Actions to function mapping, to allow for illegal python action names that
# can map to a python function.
ACTIONS = {
    "create-cloud-admin-trust": create_cloud_admin_trust,
    "create-license": create_license,
    "ghost-share": ghost_share,
    "update-trilio": update_trilio,
}


def main(args):
    hookenv._run_atstart()
    action_name = os.path.basename(args[0])
    try:
        action = ACTIONS[action_name]
    except KeyError:
        return "Action %s undefined" % action_name
    else:
        try:
            action(args)
        except Exception as e:
            hookenv.function_fail(str(e))
    hookenv._run_atexit()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
