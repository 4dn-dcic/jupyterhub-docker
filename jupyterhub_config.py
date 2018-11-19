import os
import shutil
import dockerspawner
from dockerspawner.volumenamingstrategy import escaped_format_volume_name
import boto3
import json
from dcicutils import ff_utils, s3_utils
from botocore.exceptions import ClientError


c = get_config()
s3_client = boto3.client('s3')

# get access keys for ff_utils. always use data.4dnucleome
ff_keys = s3_utils.s3Utils(env='data').get_access_keys()


def escaped_format_volume_name_and_chmod(label_template, spawner):
    # test
    volume_name = escaped_format_volume_name(label_template, spawner)
    if '_data' in volume_name:
        shutil.chown(volume_name, user='root', group='root')
        os.chmod(path, 0o444)
    return volume_name


def escape_string(in_str):
    """
    Escape a string the way DockerSpawner does, which is needed to make
    the user email match
    """
    ds_class = dockerspawner.dockerspawner.DockerSpawner
    return dockerspawner.dockerspawner.escape(
        in_str,
        safe=ds_class._docker_safe_chars,
        escape_char=ds_class._docker_escape_char
    )


def initialize_user_content(spawner):
    """
    Used to initialize the users s3-backed notebook storage.
    For initialization, ensure all notebook templates are copied
    (check every time)
    In addition, load access keys from Fourfront and add them to the
    environment variables of the notebook. Also delete previously created
    access keys used for Jupyterhub for the user
    """
    err_output = []  # keep track of errors for debugging
    username = spawner.user.name  # get the username
    list_res = s3_client.list_objects_v2(
        Bucket=os.environ['AWS_TEMPLATE_BUCKET']
    )
    # check each template individually
    for template_res in list_res.get('Contents', []):
        template_key = template_res['Key']
        user_subdir = 'user-' + escape_string(username)
        notebook_temp_key = '/'.join([user_subdir, template_key])
        try:
            s3_client.head_object(Bucket=os.environ['AWS_NOTEBOOK_BUCKET'],
                                  Key=notebook_temp_key)
        except ClientError as head_exc:
            if head_exc.response.get('Error', {}).get('Code') == '404':
                source_info = {"Bucket": os.environ['AWS_TEMPLATE_BUCKET'],
                               "Key": template_key}
                try:
                    s3_client.copy_object(Bucket=os.environ["AWS_NOTEBOOK_BUCKET"],
                                          Key=notebook_temp_key, CopySource=source_info)
                except Exception as copy_exc:
                    err_output.append({'copying_templates': str(copy_exc)})
            else:
                err_output.append({'finding_templates': str(head_exc)})

    # get the access keys and set them as environment variables for the user
    try:
        ff_user = ff_utils.get_metadata('/users/' + username, key=ff_keys)
    except Exception as user_exc:
        err_output.append({'getting_user': str(user_exc)})
    else:
        key_descrip = 'jupyterhub_key'
        search_q = ''.join(['/search/?type=AccessKey&status=current&description=',
                            key_descrip, '&user.uuid=', ff_user['uuid']])
        try:
            user_keys = ff_utils.search_metadata(search_q, key=ff_keys)
        except Exception as search_exc:
            err_output.append({'searching_keys': str(search_exc)})
        else:
            for ukey in user_keys:
                try:
                    ff_utils.patch_metadata({'status': 'deleted'}, ukey['uuid'], key=ff_keys)
                except Exception as patch_exc:
                    err_output.append({'deleting_keys': str(patch_exc)})
        # access key will be submitted by 4dn-dcic admin but belong to user
        key_body = {'user': ff_user['uuid'], 'description': key_descrip}
        try:
            key_res = ff_utils.post_metadata(key_body, 'access-keys', key=ff_keys)
        except Exception as key_exc:
            err_output.append({'post_key': str(key_exc)})
        else:
            os.environ['FF_ACCESS_KEY'] = key_res['access_key_id']
            os.environ['FF_ACCESS_SECRET'] = key_res['secret_access_key']
    os.environ['INIT_ERR_OUTPUT'] = json.dumps(err_output)


c.JupyterHub.log_level  = "DEBUG"
# attach the hook function to the spawner
c.Spawner.pre_spawn_hook = initialize_user_content
# propogate these variables to the user notebook processes
c.Spawner.env_keep.extend(['FF_ACCESS_KEY', 'FF_ACCESS_SECRET', 'INIT_ERR_OUTPUT'])
# Spawn single-user servers as Docker containers
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
# Spawn containers from this image
# by default, c.DockerSpawner.container_image uses jupyterhub/singleuser image
# with the appropriate tag that pins version. Otherwise, do something like:
# c.DockerSpawner.image = 'jupyter/scipy-notebook:8f56e3c47fec'
c.DockerSpawner.image = os.environ['DOCKER_NOTEBOOK_IMAGE']
# default `start_singleruser.sh` is included
c.DockerSpawner.cmd = os.environ.get('DOCKER_SPAWN_CMD', "start-singleuser.sh")
# can I remove these two lines?
# spawn_cmd = os.environ.get('DOCKER_SPAWN_CMD', "start-singleuser.sh")
# c.DockerSpawner.extra_create_kwargs.update({ 'command': spawn_cmd })

# Connect containers to this Docker network
network_name = os.environ['DOCKER_NETWORK_NAME']
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = network_name
# Pass the network name as argument to spawned containers
c.DockerSpawner.extra_host_config = { 'network_mode': network_name }

notebook_dir = os.environ.get('DOCKER_NOTEBOOK_DIR')
c.DockerSpawner.notebook_dir = notebook_dir

# https://stackoverflow.com/questions/51330356/jupyterhub-in-docker-container-not-able-to-connect-to-external-directory
# notebook_mount_dir in form: '/path/on/host'
notebook_mount_dir = '/home/ubuntu/data/jupyterhub-fourfront-notebooks/user-{username}'
raw_data_mount_dir = '/home/ubuntu/data/' + os.environ['AWS_RAW_FILE_BUCKET']
proc_data_mount_dir = '/home/ubuntu/data/' + os.environ['AWS_PROC_FILE_BUCKET']
# notebook_dir in form: '/path/on/container'
c.DockerSpawner.volumes = {notebook_mount_dir: {"bind": notebook_dir, "mode": "rw"},
                           raw_data_mount_dir: {"bind": '/home/jovyan/raw_data', "mode": "ro"},
                           proc_data_mount_dir: {"bind": '/home/jovyan/proc_data', "mode": "ro"}}

# allow escaped characters in volume names
c.DockerSpawner.format_volume_name = escaped_format_volume_name_and_chmod
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
c.Auth0OAuthenticator.oauth_callback_url = ['AUTH0_CALLBACK_URL']
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
