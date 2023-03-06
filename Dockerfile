# app/Dockerfile

FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/sandrohr95/green-senti-outliers-detection.git .

RUN pip3 install -r requirements.txt

EXPOSE 8051

HEALTHCHECK CMD curl --fail http://0.0.0.0:8051/_stcore/outliers

ENTRYPOINT ["streamlit", "run", "main_page.py", "--server.port=8051", "--server.address=0.0.0.0"]
