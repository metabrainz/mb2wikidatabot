FROM metabrainz/python:3.9-focal-20220315

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

# PostgreSQL client
COPY ACCC4CF8.asc /tmp/
RUN apt-key add /tmp/ACCC4CF8.asc && rm -f /tmp/ACCC4CF8.asc
ENV PG_MAJOR 12
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
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

COPY . /code
RUN pip install -r requirements.txt
RUN pip install setuptools

# runit service files
COPY ./docker/consul-template-mb2wdbot.conf /etc/consul-template-mb2wdbot.conf
COPY ./docker/wikidata-bot.service /etc/service/wikidata-bot/run
RUN chmod 755 /etc/service/wikidata-bot/run
RUN chmod 755 /code/run.py
