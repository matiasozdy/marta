FROM python:2.7-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY marta.py .
CMD [ "python", "marta.py" ]
