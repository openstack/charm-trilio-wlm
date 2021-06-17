# Overview

This charm provides the TrilioVault Workload Manager Service which forms
part of the [TrilioVault Cloud Backup solution][trilio.io].

# Usage

The TrilioVault Workload Manager Service relies on a database service, the
Keystone identity service, and RabbitMQ messaging:

    juju deploy trilio-wlm
    juju deploy mysql
    juju deploy rabbitmq-server
    juju deploy keystone
    juju add-relation trilio-wlm mysql
    juju add-relation trilio-wlm rabbitmq-server
    juju add-relation trilio-wlm keystone

TrilioVault will also need to be deployed with other services in order to
provide a fully functional TrilioVault backup solution. Refer to the
[TrilioVault Data Protection][deployment-guide] section in the deployment
guide for more information.

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

# Storage Options

TrilioVault supports NFS and S3 backends for storing workload backups. The
storage type used by TrilioVault is determined by the value in the
`backup-target-type` charm config option.

## NFS

To configure the TrilioVault Workload Manager to store backups in an NFS share,
set the `backup-target-type` option of the charm to `nfs` and set the `nfs-shares`
option of the charm to specify a valid NFS share.

    juju config trilio-wlm backup-target-type=nfs
    juju config trilio-wlm nfs-shares=10.40.3.20:/srv/triliovault

Mount settings for the NFS shares can be configured using the `nfs-options`
config option.

The TrilioVault Data Mover application will also need to be configured to use
the same nfs-share.

## S3

To configure the TrilioVault Workload Manager to store backups in an S3 share,
set the `backup-target-type` option of the charm to `s3` and set the following
configuration options to provide information regarding the S3 service:

* `tv-s3-endpoint-url` the URL of the s3 storage
* `tv-s3-secret-key` the secret key for accessing the s3 storage
* `tv-s3-access-key` the access key for accessing the s3 storage
* `tv-s3-region-name` the region for accessing the s3 storage
* `tv-s3-bucket` the s3 bucket to use to storage backups in
* `tv-s3-ssl-cert` the SSL CA to use when connecting to the s3 service

    juju config trilio-wlm tv-s3-endpoint-url=http://s3.example.com/
    juju config trilio-wlm tv-s3-secret-key=superSecretKey
    juju config trilio-wlm tv-s3-access-key=secretAccessKey
    juju config trilio-wlm tv-s3-region-name=RegionOne
    juju config trilio-wlm tv-s3-bucket=backups

# Bugs

Please report bugs on [Launchpad][lp-bugs-charm-trilio-wlm].

[lp-bugs-charm-trilio-wlm]: https://bugs.launchpad.net/charm-trilio-wlm/+filebug
[trilio.io]: https://www.trilio.io/triliovault/openstack
[deployment-guide]: https://docs.openstack.org/project-deploy-guide/charm-deployment-guide/latest/app-trilio-vault.html
