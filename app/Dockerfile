FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY pipeline.py .
COPY feature_query.sql .
COPY products.csv .
COPY model_A.joblib .
COPY model_B.joblib .
COPY normalization_params.joblib .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
