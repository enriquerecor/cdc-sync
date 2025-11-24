FROM python:3.13
WORKDIR /cdc
COPY requirements.txt requirements.txt
RUN python3 -m pip install -r requirements.txt
COPY src .
ENV PYTHONPATH="${PYTHONPATH}:/cdc"
CMD ["python3", "-m", "cdc", "inventory.customers.yml", "kafka:9092"]
