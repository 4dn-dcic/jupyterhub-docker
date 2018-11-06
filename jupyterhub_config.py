import os
import dockerspawner
from dcicutils import ff_utils, s3_utils

c = get_config()

# get access keys for ff_utils. always use data.4dnucleome
ff_keys = s3_utils.s3Utils(env='data').get_access_keys()

c.JupyterHub.log_level  = "DEBUG"

# Spawn single-user servers as Docker containers
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
# Spawn containers from this image

# by default, c.DockerSpawner.container_image uses jupyterhub/singleuser image with the appropriate tag that pins version
# otherwise, do something like:
# c.DockerSpawner.container_image = 'jupyter/scipy-notebook:8f56e3c47fec'
c.DockerSpawner.container_image = os.environ['DOCKER_NOTEBOOK_IMAGE']
# default `start_singleruser.sh` is included
spawn_cmd = os.environ.get('DOCKER_SPAWN_CMD', "start-singleuser.sh")
c.DockerSpawner.extra_create_kwargs.update({ 'command': spawn_cmd })
# Connect containers to this Docker network
network_name = os.environ['DOCKER_NETWORK_NAME']
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = network_name
# Pass the network name as argument to spawned containers
c.DockerSpawner.extra_host_config = { 'network_mode': network_name }
notebook_dir = os.environ.get('DOCKER_NOTEBOOK_DIR')
c.DockerSpawner.notebook_dir = notebook_dir
# Mount the real user's Docker volume on the host to the notebook user's
# notebook directory in the container
c.DockerSpawner.volumes = { 'jupyterhub-user-{username}': notebook_dir }

# will need something like this for s3-backed dirs
# see avillach lab example

# Mount the real user's Docker volume on the host to the notebook user's
# notebook directory in the container
# also mount a readonly and shared folder
# c.DockerSpawner.volumes = { 'jupyterhub-user-{username}': notebook_dir, 'jupyterhub-shared': os.path.join(notebook_dir, 'shared') }
# c.DockerSpawner.read_only_volumes = { 'jupyterhub-readonly': os.path.join(notebook_dir, 'readonly') }
# c.DockerSpawner.extra_create_kwargs.update({ 'volume_driver': 'local' })

# allow escaped characters in volume names
c.DockerSpawner.format_volume_name = dockerspawner.volumenamingstrategy.escaped_format_volume_name
# Remove containers once they are stopped
c.DockerSpawner.remove_containers = True
# For debugging arguments passed to spawned containers
c.DockerSpawner.debug = True

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = 'jupyterhub'
c.JupyterHub.hub_port = 8080

# TLS config
c.JupyterHub.port = 80

# Production authenticator
c.Auth0OAuthenticator.client_id = os.environ['AUTH0_CLIENT_ID']
c.Auth0OAuthenticator.client_secret = os.environ['AUTH0_CLIENT_SECRET']
c.Auth0OAuthenticator.oauth_callback_url = 'https://jupyter.4dnucleome.org/hub/oauth_callback'
c.JupyterHub.authenticator_class = 'oauthenticator.auth0.Auth0OAuthenticator'

# Development authenticator
# c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'

data_dir = os.environ.get('DATA_VOLUME_CONTAINER', '/data')
c.JupyterHub.cookie_secret_file = os.path.join(data_dir, 'jupyterhub_cookie_secret')
c.JupyterHub.db_url = os.path.join(data_dir, 'jupyterhub.sqlite')

# Whitlelist users and admins
c.Authenticator.whitelist = whitelist = set()
c.Authenticator.admin_users = admin = set()
c.JupyterHub.admin_access = True
ff_users = ff_utils.search_metadata('search/?type=User&field=email', key=ff_keys)
for ff_user in ff_users:
    if not ff_user.get('email'):
        continue
    whitelist.add(ff_user['email'])
    # base admin off of a set environment variable, for now
    if os.environ.get('ADMIN_EMAIL') == ff_user['email']:
        admin.add(ff_user['email'])
