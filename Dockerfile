FROM python

RUN mkdir -p /var/www/app

COPY requirements.txt /var/www/app

WORKDIR /var/www/app

RUN pip install -r requirements.txt

COPY main.py /var/www/app
COPY http/ /var/www/app/http/

ENTRYPOINT ["python", "main.py"]