FROM apache/airflow:2.6.0

COPY constraints-3.7.txt /constraints-3.7.txt
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --user -r /requirements.txt --constraint /constraints-3.7.txt