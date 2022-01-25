import os
import sys
import dockerspawner
import boto3
import json
import datetime
import string
from dcicutils import ff_utils, s3_utils


# Initialize JH
c = get_config()

# get access keys and jupyterhub token for dcicutils. always use 'data' env
s3_client = boto3.client('s3')
s3_helper = s3_utils.s3Utils(env='data')
ff_keys = s3_helper.get_ff_key()
jh_token = s3_helper.get_jupyterhub_key()


# Helper Functions


def escape_string(in_str):
    """
    Escape a string the way DockerSpawner does, which is needed to make
    the user email match
    NOTE: since dockerspawner 12.0, the old escape method is deprecated
    and in fact does not function at all since the referenced fields
    were removed.
    This change has to do with DNS/container naming and should be scrutinized.
    Dockerspawner claims a new convention is used, but can disable it.
    """
    _docker_safe_chars = set(string.ascii_letters + string.digits + '-')
    _docker_escape_char = '_'
    return dockerspawner.dockerspawner.escape(
        in_str,
        safe=_docker_safe_chars,
        escape_char=_docker_escape_char
    )


def clear_old_access_keys():
    """ Helper method that deletes access key information currently in the env """
    if 'FF_ACCESS_KEY' in os.environ:
        os.environ['FF_ACCESS_KEY'] = ''
    if 'FF_SECRET_KEY' in os.environ:
        os.environ['FF_SECRET_KEY'] = ''


def recompute_ff_keys(err_output):
    """ Helper method used in the pre/post spawn hooks that will recompute
        the access keys needed in spawner context. This is safe to do since
        the spawner does not propogate this information to the child container
    """
    try:
        ff_keys = s3_helper.get_ff_key()
    except Exception as e:
        err_output.append({'getting_access_keys': str(e)})
        clear_old_access_keys()
        return None
    return ff_keys


def initialize_user_content(spawner):
    """
    Used to initialize the users s3-backed notebook storage.
    For initialization, ensure all notebook templates are copied
    (check every time)
    In addition, load access keys from Fourfront and add them to the
    environment variables of the notebook. Also delete previously created
    access keys used for Jupyterhub for the user
    Also initialized a TrackingItem of type jupyterhub_session to track some
    basic information on the JH session
    This function should also be heavily scrutinized, as it has been a source of
    error in the past since we first acquire admin keys then context switch
    """
    err_output = []  # keep track of errors for debugging

    # grab this info fresh every time
    ff_keys = recompute_ff_keys(err_output)

    username = spawner.user.name  # get the username
    list_res = s3_client.list_objects_v2(
        Bucket=os.environ['AWS_TEMPLATE_BUCKET']
    )

    # check each template individually
    for template_res in list_res.get('Contents', []):
        template_key = template_res['Key']
        user_subdir = 'user-' + escape_string(username)
        notebook_temp_key = '/'.join([user_subdir, template_key])
        source_info = {'Bucket': os.environ['AWS_TEMPLATE_BUCKET'],
                       'Key': template_key}
        try:  # always replace templates
            s3_client.copy_object(Bucket=os.environ['AWS_NOTEBOOK_BUCKET'],
                                  Key=notebook_temp_key, CopySource=source_info)
        except Exception as copy_exc:
            err_output.append({'copying_templates': str(copy_exc)})

    # get the access keys and set them as environment variables for the user
    try:
        ff_user = ff_utils.get_metadata('/users/' + username, key=ff_keys)
    except Exception as user_exc:
        err_output.append({'getting_user': str(user_exc)})
        clear_old_access_keys()  # if we get here, old access key state must be cleared.
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
            clear_old_access_keys()  # if we get here, old access key state must be cleared.
        else:
            os.environ['FF_ACCESS_KEY'] = key_res['access_key_id']
            os.environ['FF_ACCESS_SECRET'] = key_res['secret_access_key']

        # intialize a tracking item for the session and store its uuid in env
        # set `submitted_by` manually to allow user to edit
        tracking_body = {
            'jupyterhub_session': {
                'date_initialized': datetime.datetime.utcnow().isoformat() + '+00:00',
                'user_uuid': ff_user['uuid']
            },
            'tracking_type': 'jupyterhub_session',
            'submitted_by': ff_user['uuid']
        }
        try:
            track_res = ff_utils.post_metadata(tracking_body, 'tracking-items', key=ff_keys)
        except Exception as track_exc:
            err_output.append({'tracking_item': str(track_exc)})
        else:
            os.environ['FF_TRACKING_ID'] = track_res['@graph'][0]['uuid']

    os.environ['INIT_ERR_OUTPUT'] = json.dumps(err_output)


def finalize_user_content(spawner):
    """
    This function is called after the singleuser notebook stops.
    Responsible for:
    - adding date_culled to the TrackingItem given by FF_TRACKING_ID
    """
    # grab this info fresh every time
    err_output = []
    ff_keys = recompute_ff_keys(err_output)

    if not os.environ.get('FF_TRACKING_ID'):
        return
    # get current item
    track_id = os.environ['FF_TRACKING_ID']
    try:
        track_res = ff_utils.get_metadata(track_id, key=ff_keys)
    except:
        pass  # Nothing to do here
    else:
        session = track_res.get('jupyterhub_session')
        if session and isinstance(session, dict):
            session['date_culled'] = datetime.datetime.utcnow().isoformat() + '+00:00'
            try:
                ff_utils.patch_metadata({'jupyterhub_session': session}, track_id, key=ff_keys)
            except:
                pass


# JH Config options


# Logging
c.JupyterHub.log_level  = 'DEBUG'

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = 'jupyterhub'
c.JupyterHub.hub_port = 8080
c.JupyterHub.shutdown_on_logout = True  # shutdown user notebooks on logout

# TLS config
c.JupyterHub.port = 80

# Configure idle culler service (stop idle user containers)
# This used to be a Python script we had to grab directly, but is now
# fully integrated as a (non-admin) hub service
c.JupyterHub.services = [
    {
        'name': 'idle-culler',
        'command': [sys.executable, '-m', 'jupyterhub_idle_culler', '--timeout=3600'],
    }
]
c.JupyterHub.load_roles = [
    {
        'name': 'list-and-cull', # name the role
        'services': [
            'idle-culler', # assign the service to this role
        ],
        'scopes': [
            # declare what permissions the service should have
            'list:users', # list users
            'read:users:activity', # read user last-activity
            'admin:servers', # start/stop servers
        ],
    }
]

# JH Authentication Config
c.JupyterHub.authenticator_class = 'oauthenticator.auth0.Auth0OAuthenticator'

# Production authenticator
c.Auth0OAuthenticator.client_id = os.environ['AUTH0_CLIENT_ID']
c.Auth0OAuthenticator.client_secret = os.environ['AUTH0_CLIENT_SECRET']
c.Auth0OAuthenticator.oauth_callback_url = os.environ['AUTH0_CALLBACK_URL']
c.Auth0OAuthenticator.auth0_subdomain = os.environ['AUTH0_DOMAIN']

# Development authenticator (comment out above and uncomment below to enable)
# c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'

# Data configuration
data_dir = os.environ['DATA_VOLUME_CONTAINER']
c.JupyterHub.cookie_secret_file = os.path.join(data_dir, 'jupyterhub_cookie_secret')
c.JupyterHub.db_url = os.path.join(data_dir, 'jupyterhub.sqlite')

# User Configuration
allowed_users = set()
blocked_users = set()
admin = set()
c.JupyterHub.admin_access = True
# Grab THE FIRST of potentially many comma-separated admin emails, lower-cased
# Change this when >1 admin is desired - Will 21 Jan 2022
admin_emails = [email.strip().lower() for email in os.environ.get('ADMIN_EMAILS', '').split(',')]
# Grab email, lab info on all users
ff_users = ff_utils.search_metadata('search/?type=User&field=email&field=lab', key=ff_keys)
for ff_user in ff_users:
    email, lab = ff_user.get('email'), ff_user.get('lab')
    # Allow users into JH if they have both email and lab fields
    if not email or not lab:
        print(f'Blocking user {email}')
        blocked_users.add(email)
        continue
    else:
        allowed_users.add(email)

        # If first admin email from before is located, add it to admin set
        if email.lower() in admin_emails:
            admin.add(email)

# Set these sets in the hub
c.Authenticator.allowed_users = allowed_users
c.Authenticator.blocked_users = blocked_users
c.Authenticator.admin_users = admin

# add API token to the instance. Use **only** the first admin email
# XXX: this interaction is deprecated and needs to be redone using c.JupyterHub.service_tokens - Will 21 Jan 2022
if admin_emails:
    c.JupyterHub.api_tokens = {
        jh_token['secret']: admin_emails[0],
    }

# Spawner options - this is the component that brings up user notebooks
# Spawn single-user servers as Docker containers
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

# Ensure initialize_user_content and finalize_user_content run pre/post user container spawn
c.Spawner.pre_spawn_hook = initialize_user_content
c.Spawner.post_stop_hook = finalize_user_content

# Propagate ONLY these variables to the user notebook processes
c.Spawner.env_keep.extend(['FF_ACCESS_KEY', 'FF_ACCESS_SECRET',
                           'INIT_ERR_OUTPUT', 'FF_TRACKING_ID'])
# Limit the memory use for single-user servers
c.Spawner.mem_limit = '1G'

# Spawn containers from the 4dn-docker-v2 image
c.DockerSpawner.image = os.environ['DOCKER_NOTEBOOK_IMAGE']
# default `start_singleuser.sh` is included and is what we use - can be overridden
# in docker-compose.yml
c.DockerSpawner.cmd = os.environ.get('DOCKER_SPAWN_CMD', 'start-singleuser.sh')

# Connect containers to this Docker network
# network_name = 'bridge'  # unused?
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = os.environ['DOCKER_NETWORK_NAME']

# disable new escape behavior, see https://github.com/jupyterhub/dockerspawner/pull/414
c.DockerSpawner.escape = 'legacy'

# Point to notebook storage
notebook_dir = os.environ['DOCKER_NOTEBOOK_DIR']
c.DockerSpawner.notebook_dir = notebook_dir

# Mount volumes from host machine
# https://stackoverflow.com/questions/51330356/jupyterhub-in-docker-container-not-able-to-connect-to-external-directory
# notebook_mount_dir in form: '/path/on/host'
notebook_mount_dir = '/home/ubuntu/data/jupyterhub-fourfront-notebooks/user-{username}'
raw_data_mount_dir = '/home/ubuntu/data/' + os.environ['AWS_RAW_FILE_BUCKET']
open_data_mount_dir = '/home/ubuntu/data/' + os.environ['AWS_OPEN_DATA_BUCKET']
proc_data_mount_dir = '/home/ubuntu/data/' + os.environ['AWS_PROC_FILE_BUCKET']
# notebook_dir in form: '/path/on/container'
c.DockerSpawner.volumes = {notebook_mount_dir: {'bind': notebook_dir, 'mode': 'rw'},
                           raw_data_mount_dir: {"bind": '/home/jovyan/raw_data', 'mode': 'ro'},
                           open_data_mount_dir: {"bind": '/home/jovyan/open_data', 'mode': 'ro'},
                           proc_data_mount_dir: {'bind': '/home/jovyan/proc_data', 'mode': 'ro'}}

# allow escaped characters in volume names
c.DockerSpawner.format_volume_name = dockerspawner.volumenamingstrategy.escaped_format_volume_name
# Remove containers once they are stopped
c.DockerSpawner.remove = True
# For debugging arguments passed to spawned containers
c.DockerSpawner.debug = True
