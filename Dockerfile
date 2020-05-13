FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    sudo \
    git \
    wget \
    r-base \
    && apt-get clean

RUN git clone https://github.com/kvgallagher/SEIR_COVID19 && \
    mkdir /input && \
    mkdir /output