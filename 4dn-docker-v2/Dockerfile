FROM jupyter/minimal-notebook:ubuntu-20.04
MAINTAINER William Ronchetti (william_ronchetti@hms.harvard.edu)

USER root
WORKDIR /tools

# 0. Get Python 3.8
ARG conda_env=python38
ARG py_ver=3.8
RUN mamba create --quiet --yes -p "${CONDA_DIR}/envs/${conda_env}" python=${py_ver} ipython ipykernel && \
    mamba clean --all -f -y

# create Python 3.8 environment and link it to jupyter
RUN "${CONDA_DIR}/envs/${conda_env}/bin/python" -m ipykernel install --user --name="${conda_env}" && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"
ENV PATH "${CONDA_DIR}/envs/${conda_env}/bin:${PATH}"
ENV CONDA_DEFAULT_ENV ${conda_env}

# 1. general updates & installing necessary Linux components
RUN apt-get update -y && apt-get install -y \
    bc \
    bzip2 \
    curl \
    g++ \
    gcc \
    git \
    less \
    libbz2-dev \
    libcurl4-openssl-dev \
    liblzma-dev \
    libncurses-dev \
    libssl-dev \
    libtbb-dev \
    make \
    libpng-dev \
    time \
    unzip \
    vim \
    wget \
    zlib1g-dev \
    liblz4-tool \
    libmysqlclient-dev

## SOFTWARE: samtools
## VERSION: 1.2
## TYPE: file format converter
## SOURCE_URL: https://github.com/samtools/samtools
RUN wget https://github.com/samtools/samtools/releases/download/1.2/samtools-1.2.tar.bz2 \
    && tar -xjf samtools-1.2.tar.bz2 \
    && cd samtools-1.2 \
    && make \
    && cd .. \
    && ln -s samtools-1.2 samtools

## SOFTWARE: pairix
## VERSION: 0.3.6
## TYPE: file format converter,indexer
## SOURCE_URL: https://github.com/4dn-dcic/pairix
RUN wget https://github.com/4dn-dcic/pairix/archive/0.3.6.tar.gz \
    && tar -xzf 0.3.6.tar.gz \
    && rm 0.3.6.tar.gz \
    && cd pairix-0.3.6 \
    && make \
    && cd .. \
    && ln -s pairix-0.3.6 pairix

## SOFTWARE: bedtools
## VERSION: 2.26.0
## TYPE: filter
## SOURCE_URL: https://github.com/arq5x/bedtools2
RUN wget https://github.com/arq5x/bedtools2/releases/download/v2.26.0/bedtools-2.26.0.tar.gz \
    && tar -zxvf bedtools-2.26.0.tar.gz \
    && cd bedtools2 \
    && make \
    && cd ..

## SOFTWARE: kentUtils
## VERSION: v302.1.0
## TYPE: file format converter
## SOURCE_URL: https://github.com/ENCODE-DCC/kentUtils
RUN git clone https://github.com/ENCODE-DCC/kentUtils \
    && cd kentUtils/ \
    && git checkout v302.1.0 \
    && make \
    && cd ..

# straw
RUN git clone https://github.com/aidenlab/straw


# set path
ENV PATH=/tools/samtools/:$PATH
ENV PATH=/tools/pairix/bin/:/tools/pairix/util/:$PATH
ENV PATH=/tools/pairix/util/bam2pairs/:$PATH
ENV PATH=/tools/bedtools2/bin/:$PATH
ENV PATH=/tools/kentUtils/bin/:$PATH

# supporting UTF-8
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

USER jovyan
WORKDIR /home/jovyan/work

# Install package (into venv)
COPY singleuser-requirements.txt requirements.txt
RUN pip install wheel numpy
RUN pip install -r requirements.txt
RUN echo "conda activate python38" >> ~/.bashrc

## Add necessary custom JS file
RUN mkdir -p /home/jovyan/.jupyter/custom
COPY custom.js /home/jovyan/.jupyter/custom/

CMD ["bash"]
