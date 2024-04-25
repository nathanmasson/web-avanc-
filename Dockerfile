FROM python:3.7-alpine

COPY inf349.py .
RUN apk update && \
    apk add --no-cache postgresql-dev gcc python3-dev musl-dev
RUN pip install peewee flask rq psycopg2 flask-cors

VOLUME /data
EXPOSE 5000

ENV REDIS_URL redis://localhost
ENV DB_HOST host.docker.internal
ENV DB_USER user
ENV DB_PASSWORD pass
ENV DB_PORT 5432
ENV DB_NAME inf349

CMD FLASK_APP=app/inf349 FLASK_DEBUG=True flask run

