FROM jupyter/minimal-notebook:8ccdfc1da8d5
## This image is based on ubuntu 18.04
MAINTAINER Soo Lee (duplexa@gmail.com)

USER root
WORKDIR /tools

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


# installing python3.5 & pip
RUN apt-get update -y && apt-get install -y \
    python3-minimal \
    python3-setuptools \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python3 get-pip.py \
    && ln -s /usr/bin/python3.6 /tools/python


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

## SOFTWARE: cooler
## VERSION: 0.7.11
## TYPE: aggregator,normalizer
## SOURCE_URL: https://github.com/mirnylab/cooler
RUN pip3 install cooler==0.7.11

## SOFTWARE: pairtools
## COMMIT: 0.2.0
## TYPE: file format converter,sorter,annotater,filter
## SOURCE_URL: https://github.com/mirnylab/pairsamtools
RUN pip3 install numpy Cython click pairtools

## other python libraries
RUN pip3 install scipy matplotlib pandas h5py pyBigWig


CMD ["bash"]

