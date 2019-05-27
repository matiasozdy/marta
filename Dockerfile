MAINTAINER Matias Ozdy (matiasozdy@gmail.com)
FROM python:3.7-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY marta.py .
CMD [ "python", "marta.py" ]
