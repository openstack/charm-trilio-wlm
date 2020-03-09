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

# Configuration Options

TODO

# Restrictions

