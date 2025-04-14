FROM python:3.9-alpine

RUN apk add --no-cache \
    build-base cairo-dev cairo cairo-tools \
    # pillow dependencies
    jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev hidapi-dev


RUN mkdir app

ADD ./src/main.py ./src/StreamDeckMQTT.py app/src/
ADD requirements.txt app/requirements.txt

RUN cd app
RUN python -m venv .

RUN pip install -r app/requirements.txt

WORKDIR "/app"

CMD [ "python", "src/main.py"]