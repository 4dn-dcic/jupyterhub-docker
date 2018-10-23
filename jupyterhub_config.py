import os

c = get_config()

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
# Remove containers once they are stopped
c.DockerSpawner.remove_containers = True
# For debugging arguments passed to spawned containers
c.DockerSpawner.debug = True

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = 'jupyterhub'
c.JupyterHub.hub_port = 8080

# TLS config
# c.JupyterHub.port = 443
# c.JupyterHub.ssl_key = os.environ['SSL_KEY']
# c.JupyterHub.ssl_cert = os.environ['SSL_CERT']

# Development port
c.JupyterHub.port = 8888
c.JupyterHub.ssl_key = os.environ['SSL_KEY']
c.JupyterHub.ssl_cert = os.environ['SSL_CERT']

# Authenticate users with Auth0 OAuth
#c.Auth0OAuthenticator.client_id = os.environ['AUTH0_CLIENT_ID']
#c.Auth0OAuthenticator.client_secret = os.environ['AUTH0_CLIENT_SECRET']
#c.Auth0OAuthenticator.oauth_callback_url = os.environ['AUTH0_CALLBACK_URL']
#c.Auth0OAuthenticator.webtask_base_url = 'https://avillachlab.us.webtask.io/connection_details_base64/'
#c.JupyterHub.authenticator_class = 'oauthenticator.auth0.Auth0OAuthenticator'

# Development authenticator
c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'

data_dir = os.environ.get('DATA_VOLUME_CONTAINER', '/data')
c.JupyterHub.cookie_secret_file = os.path.join(data_dir, 'jupyterhub_cookie_secret')
c.JupyterHub.db_url = os.path.join(data_dir, 'jupyterhub.sqlite')

# Whitlelist users and admins
c.Authenticator.whitelist = whitelist = set()
c.Authenticator.admin_users = admin = set()
c.JupyterHub.admin_access = True
pwd = os.path.dirname(__file__)
with open(os.path.join(pwd, 'userlist')) as f:
    for line in f:
        if not line:
            continue
        parts = line.split()
        # in case of newline at the end of userlist file
        if len(parts) >= 1:
            name = parts[0]
            whitelist.add(name)
            if len(parts) > 1 and parts[1] == 'admin':
                admin.add(name)
