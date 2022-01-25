#################
jupyterhub-docker
#################

Note that the Confluence Page on the JH server has more detailed notes on working with the hub.

###########
What is JH?
###########

This repository is intended for use on an Ubuntu EC2 instance running Docker in the 4DN AWS Cloud (4dn-dcic).
It will not function outside of this account as the resources it accesses are specific to that account. The hub
allows authenticated and lab associated users to access Python notebooks that give more convenient access to
the 4DN metadata. They are able to interact with both the metadata and the raw files themselves on S3 via a custom
mounting strategy. User notebooks are also backed up on S3, and some example notebooks are provided.

*********
Structure
*********

See JH documentation on how JH itself works internally. We build a custom hub from ``Dockerfile.jupyterhub`` and
singleuser container ``4dn-docker-v2/Dockerfile``. The hub launches our custom singleuser notebook containers when
users log into the hub. Their user access keys are automatically sourced and used. Auth0 authentication through
the portal is also used for login.

