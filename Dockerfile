FROM python:3.7-alpine

COPY inf349.py .
RUN pip install peewee flask

VOLUME /data
EXPOSE 5000
ENV DATABASE /commandes.db
CMD FLASK_APP=inf349 flask init-db
CMD FLASK_DEBUG=True FLASK_APP=inf349 flask run
CMD FLASK_APP=inf349 flask worker
