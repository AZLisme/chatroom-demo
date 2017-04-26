FROM python:3.6
MAINTAINER AZLisme <helloazl@icloud.com>
WORKDIR /src
ADD static static
ADD templates templates
ADD main.py main.py
ADD requirements.txt requirements.txt
ADD config.py config.py
RUN pip install -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["python", "main.py"]