# app/Dockerfile

FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip3 install -r requirements.txt

EXPOSE 8051

COPY . /app

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "main_page.py", "--server.port=8051", "--server.address=0.0.0.0", "--server.baseUrlPath=/green-senti-outlier-detection"]
