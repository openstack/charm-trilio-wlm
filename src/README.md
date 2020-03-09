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

# Installing a TrilioVault License

In order to operate TrilioVault a license for the deployment must be
installed. Attach the license file provided by Trilio to the application:

    juju attach-resource trilio-wlm license=mylicense.lic

and then execute the 'create-license' action:

    juju run-action --wait trilio-wlm/leader create-license

The resource may be included as part of a bundle but the action must
be run post deployment to complete configuration of the TrilioVault
service.

Alternatively this may be completed via the Horizon plugin for
TrilioVault in the OpenStack Dashboard.

# Configuration Options

TODO

# Restrictions

