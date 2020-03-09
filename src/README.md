# Overview

TODO

# Usage

TODO

# Creating trust with the Cloud Admin account

In order for TrilioVault to backup services running on the OpenStack Cloud
application trust must be granted from the Trilio WLM service account to
the Cloud Admin account using the Admin role.  This is completed using the
'create-cloud-admin-trust' action post deployment:

    juju run-action --wait trilio-wlm/leader create-cloud-admin-trust \
        password=<cloud admin password>

This allows the Trilio WLM service account to impersonate the Cloud Admin
account in order to access full details of services being protected.

Trusts can be listed and managed using the 'openstack trust ...' set of
OSC commands.

# Configuration Options

TODO

# Restrictions

