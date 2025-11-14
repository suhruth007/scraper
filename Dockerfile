FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=src/app
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "app.__init__:create_app()", "--bind", "0.0.0.0:5000", "--workers", "3", "--threads", "2"]
