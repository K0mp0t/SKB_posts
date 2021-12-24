FROM python:3.8
COPY . /api
WORKDIR /api
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir
CMD export FLASK_APP=app & flask run --host=0.0.0.0 --port=20210