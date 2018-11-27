FROM openjdk:10-jre-slim
ENV WAVES_NETWORK_BYTE="C"
ENV WAVES_AVERAGE_BLOCK_DELAY="60s"
ENV WAVES_SEED_COUNT=5
ENV WAVES_INITIAL_BALANCE=10000000000000000


MAINTAINER Inal Kardanov <ikardanov@wavesplatform.com> (@ikardanov)

# Install sbt

RUN apt-get update -y && apt-get install gnupg -y

RUN echo "deb https://dl.bintray.com/sbt/debian /" | tee -a /etc/apt/sources.list.d/sbt.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2EE0EA64E40A89B84B2DF73499E82A75642AC823 \
    && apt-get update -y \
    && apt-get install git curl sbt -y

# Install python
RUN apt-get update -y && apt-get install -y python3 \
    python3-pip \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip
RUN pip3 install requests pyhocon

RUN mkdir /waves-genesis
ADD entrypoint.sh /
ADD genesis-settings-generator.py /

WORKDIR /waves-genesis
RUN git clone https://github.com/wavesplatform/Waves.git

WORKDIR /waves-genesis/Waves
RUN git fetch --all --tags --prune
RUN git checkout tags/v0.15.1 -b 0-15-1


RUN sbt "test:runMain tools.GenesisBlockGenerator /waves-genesis/Waves/src/test/resources/genesis.example.conf"

WORKDIR /waves-genesis
VOLUME /waves-mnt

RUN ["chmod", "+x", "/entrypoint.sh"]

ENTRYPOINT ["/entrypoint.sh"]