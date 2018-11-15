ARG DOCKER_NOTEBOOK_IMAGE
FROM $DOCKER_NOTEBOOK_IMAGE
ARG JUPYTERHUB_VERSION
USER jovyan
WORKDIR /home/jovyan/work
RUN python3 -m pip install --no-cache jupyterhub==$JUPYTERHUB_VERSION
RUN mkdir lalala
