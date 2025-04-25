set DJANGO_SETTINGS_MODULE=tuyendung.settings
daphne tuyendung.asgi:application
sudo service redis-server start

celery -A tuyendung worker --pool=solo -l info

celery -A tuyendung beat -l info