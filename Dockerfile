ARG PYTHON_VERSION=3.13
ARG BASE_IMAGE_DATE=20260216
FROM metabrainz/python:$PYTHON_VERSION-$BASE_IMAGE_DATE

ENV DOCKERIZE_VERSION=v0.10.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

# PostgreSQL client
COPY ACCC4CF8.asc /tmp/
RUN apt-key add /tmp/ACCC4CF8.asc && rm -f /tmp/ACCC4CF8.asc
ENV PG_MAJOR=18
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ noble-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
            build-essential \
            git \
            libpq-dev \
            libffi-dev \
            libssl-dev \
            postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /code
WORKDIR /code

COPY pyproject.toml uv.lock /code/
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv sync --frozen --no-dev

COPY . /code

# Consul Template service is already set up with the base image.
# Just need to copy the configuration.
COPY ./docker/consul-template.conf /etc/consul-template.conf
COPY ./docker/wikidata-bot.service /etc/service/wikidata-bot/run
RUN chmod 755 /etc/service/wikidata-bot/run
RUN chmod 755 /code/run.py
