FROM metabrainz/python:3.8

ENV DOCKERIZE_VERSION v0.2.0
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       git \
                       libpq-dev \
                       libffi-dev \
                       libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL client
COPY ACCC4CF8.asc /tmp/
RUN apt-key add /tmp/ACCC4CF8.asc && rm -f /tmp/ACCC4CF8.asc
ENV PG_MAJOR 12
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /code
WORKDIR /code

COPY . /code
RUN pip install -r requirements.txt
RUN pip install setuptools

# Consul Template service is already set up with the base image.
# Just need to copy the configuration.
COPY ./docker/consul-template.conf /etc/consul-template.conf
COPY ./docker/wikidata-bot.service /etc/service/wikidata-bot/run
RUN chmod 755 /etc/service/wikidata-bot/run
RUN chmod 755 /code/run.py
