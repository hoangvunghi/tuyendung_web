set DJANGO_SETTINGS_MODULE=tuyendung.settings
daphne tuyendung.asgi:application
sudo service redis-server start