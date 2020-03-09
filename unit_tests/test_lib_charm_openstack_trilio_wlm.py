# Copyright 2016 Canonical Ltd
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


class Helper(test_utils.PatchHelper):
    def setUp(self):
        super().setUp()
        self.patch_release(trilio_wlm.TrilioWLMCharm.release)


class TestTrilioWLMCharmAdapterProperties(Helper):

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
