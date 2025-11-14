web: gunicorn app.__init__:create_app() --log-file -
worker: celery -A src.app.tasks.celery worker --loglevel=info
