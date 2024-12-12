FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p db log

EXPOSE 16999

CMD ["python", "obgym_core.py"]
