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


import mock

import charm.openstack.trilio_wlm as trilio_wlm
import charms_openstack.test_utils as test_utils

import charms_openstack.charm.core as co_core
import charms_openstack.plugins.trilio as co_trilio


class Helper(test_utils.PatchHelper):
    def setUp(self):
        super().setUp()
        self.patch_release(trilio_wlm.TrilioWLMBaseCharm.release)


class TestTrilioWLM(test_utils.PatchHelper):

    def test_selector(self):
        _safe_gcif = co_core._get_charm_instance_function
        save_releases = co_trilio._trilio_releases
        co_core._get_charm_instance_function = None
        self.patch_object(co_trilio.fetch.apt_pkg, 'version_compare')

        def _version_compare(ver1, ver2):
            if float(ver1) > float(ver2):
                return 1
            elif float(ver1) < float(ver2):
                return -1
            else:
                return 0

        self.version_compare.side_effect = _version_compare
        co_trilio.make_trilio_get_charm_instance_handler()

        test_endpoint = 'nfs://10.0.0.10:2049/mypath'
        pre_42_encode = 'bmZzOi8vMTAuMC4wLjEwOjIwNDkvbXlwYXRo'
        post_42_encode = 'L215cGF0aA=='

        charm_class = co_core.get_charm_instance(release='stein_4.1')
        self.assertEqual(
            charm_class.python_version,
            2)
        self.assertIn('python3-workloadmgrclient', charm_class.base_packages)
        self.assertNotIn('python3-retrying', charm_class.base_packages)
        self.assertEqual(
            charm_class._encode_endpoint(test_endpoint),
            pre_42_encode)

        charm_class = co_core.get_charm_instance(release='stein_4.2')
        self.assertEqual(
            charm_class.python_version,
            3)
        self.assertIn('python3-workloadmgrclient', charm_class.base_packages)
        self.assertNotIn('python3-retrying', charm_class.base_packages)
        self.assertEqual(
            charm_class._encode_endpoint(test_endpoint),
            post_42_encode)

        charm_class = co_core.get_charm_instance(release='ussuri_4.1')
        self.assertEqual(
            charm_class.python_version,
            3)
        self.assertIn('python3-workloadmgrclient', charm_class.base_packages)
        self.assertIn('python3-retrying', charm_class.base_packages)
        self.assertEqual(
            charm_class._encode_endpoint(test_endpoint),
            pre_42_encode)

        charm_class = co_core.get_charm_instance(release='ussuri_4.2')
        self.assertEqual(
            charm_class.python_version,
            3)
        self.assertIn('python3-workloadmgrclient', charm_class.base_packages)
        self.assertIn('python3-retrying', charm_class.base_packages)
        self.assertEqual(
            charm_class._encode_endpoint(test_endpoint),
            post_42_encode)

        co_trilio._trilio_releases = save_releases
        co_core._get_charm_instance_function = _safe_gcif


class TestTrilioWLMCharmStein41AdapterProperties(Helper):

    _endpoints = {
        "neutron": {"internal": "http://neutron-controller"},
        "cinderv2": {"internal": "http://cinder-controller"},
        "glance": {"internal": "http://glance-controller"},
        "nova": {"internal": "http://nova-controller"},
    }

    def test_url_handlers(self):
        identity_service = mock.MagicMock()
        identity_service.relation.endpoint_checksums.return_value = (
            self._endpoints
        )
        self.assertEqual(
            trilio_wlm.nova_url(identity_service), "http://nova-controller"
        )
        self.assertEqual(
            trilio_wlm.cinder_url(identity_service), "http://cinder-controller"
        )
        self.assertEqual(
            trilio_wlm.glance_url(identity_service), "http://glance-controller"
        )
        self.assertEqual(
            trilio_wlm.neutron_url(identity_service),
            "http://neutron-controller",
        )

        self.assertEqual(
            trilio_wlm._get_internal_url(identity_service, "barbican"), None
        )


class TestTrilioWLMCharmStein41TrustActions(Helper):
    def test_create_trust(self):
        identity_service = mock.MagicMock()
        identity_service.admin_domain_id.return_value = (
            "8e7b72adde7f4a15a4f23620a1d0cfd1"
        )
        identity_service.admin_project_id.return_value = (
            "56446f91358b40d3858276fe9680f5d8"
        )
        identity_service.service_protocol.return_value = "http"
        identity_service.service_host.return_value = "localhost"
        identity_service.service_port.return_value = "5000"
        identity_service.service_tenant.return_value = "admin"
        self.patch_object(trilio_wlm.subprocess, "check_call")
        self.patch_object(trilio_wlm.hookenv, "config")
        self.config.return_value = "TestRegionA"
        trilio_wlm_charm = trilio_wlm.TrilioWLMCharmStein41()
        trilio_wlm_charm.create_trust(identity_service, "test-ca-password")
        self.config.assert_called_with("region")
        self.check_call.assert_called_with(
            [
                "workloadmgr",
                "--os-username",
                "admin",
                "--os-password",
                "test-ca-password",
                "--os-auth-url",
                "http://localhost:5000/v3",
                "--os-user-domain-name",
                "admin_domain",
                "--os-project-domain-id",
                "8e7b72adde7f4a15a4f23620a1d0cfd1",
                "--os-project-id",
                "56446f91358b40d3858276fe9680f5d8",
                "--os-project-name",
                "admin",
                "--os-region-name",
                "TestRegionA",
                "trust-create",
                "--is_cloud_trust",
                "True",
                "Admin",
            ]
        )

    def test_create_trust_not_ready(self):
        identity_service = mock.MagicMock()
        identity_service.base_data_complete.return_value = False
        trilio_wlm_charm = trilio_wlm.TrilioWLMCharmStein41()
        with self.assertRaises(trilio_wlm.IdentityServiceIncompleteException):
            trilio_wlm_charm.create_trust(identity_service, "test-ca-password")


class TestTrilioWLMCharmStein41LicenseActions(Helper):
    def test_create_license(self):
        identity_service = mock.MagicMock()
        identity_service.service_domain_id.return_value = (
            "8e7b72adde7f4a15a4f23620a1d0cfd1"
        )
        identity_service.service_tenant_id.return_value = (
            "56446f91358b40d3858276fe9680f5d8"
        )
        identity_service.service_protocol.return_value = "http"
        identity_service.service_host.return_value = "localhost"
        identity_service.service_port.return_value = "5000"
        identity_service.service_username.return_value = "triliowlm"
        identity_service.service_password.return_value = "testingpassword"
        identity_service.service_tenant.return_value = "admin"
        self.patch_object(trilio_wlm.subprocess, "check_call")
        self.patch_object(trilio_wlm.hookenv, "config")
        self.patch_object(trilio_wlm.hookenv, "resource_get")
        self.config.return_value = "TestRegionA"
        self.resource_get.return_value = "/var/lib/charm/license.lic"
        trilio_wlm_charm = trilio_wlm.TrilioWLMCharmStein41()
        trilio_wlm_charm.create_license(identity_service)
        self.config.assert_called_with("region")
        self.resource_get.assert_called_with("license")
        self.check_call.assert_called_with(
            [
                "workloadmgr",
                "--os-username",
                "triliowlm",
                "--os-password",
                "testingpassword",
                "--os-auth-url",
                "http://localhost:5000/v3",
                "--os-user-domain-name",
                "service_domain",
                "--os-project-domain-id",
                "8e7b72adde7f4a15a4f23620a1d0cfd1",
                "--os-project-id",
                "56446f91358b40d3858276fe9680f5d8",
                "--os-project-name",
                "admin",
                "--os-region-name",
                "TestRegionA",
                "license-create",
                "/var/lib/charm/license.lic",
            ]
        )

    def test_create_license_missing(self):
        identity_service = mock.MagicMock()
        identity_service.base_data_complete.return_value = False
        self.patch_object(trilio_wlm.hookenv, "resource_get")
        self.resource_get.return_value = False
        trilio_wlm_charm = trilio_wlm.TrilioWLMCharmStein41()
        with self.assertRaises(trilio_wlm.LicenseFileMissingException):
            trilio_wlm_charm.create_license(identity_service)

    def test_create_license_not_ready(self):
        identity_service = mock.MagicMock()
        identity_service.base_data_complete.return_value = False
        self.patch_object(trilio_wlm.hookenv, "resource_get")
        self.resource_get.return_value = "/var/lib/charm/license.lic"
        trilio_wlm_charm = trilio_wlm.TrilioWLMCharmStein41()
        with self.assertRaises(trilio_wlm.IdentityServiceIncompleteException):
            trilio_wlm_charm.create_license(identity_service)
