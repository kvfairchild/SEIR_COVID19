# Base image https://hub.docker.com/u/rocker/
FROM rocker/r-base:latest

RUN git clone https://github.com/kvgallagher/SEIR_COVID19 && \
    mkdir /input && \
    mkdir /output