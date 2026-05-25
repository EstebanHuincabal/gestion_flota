pip install -r requirements.txt
# 'daphne' está primero en INSTALLED_APPS → runserver usa ASGI automáticamente (WebSockets activos)
python manage.py runserver 0.0.0.0:8000
