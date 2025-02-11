![example workflow](https://github.com/Karramb/kittygram_final/actions/workflows/main.yml/badge.svg)

Проект позволяет публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на других авторов. Так же на сайте возможнос создать список продуктов, которые необходимы для приготовления того или иного рецепта и скачать их отдельным файлом.

# Стек
- Django==3.2.3
- django-filter==23.1
- django-admin-autocomplete-filter==0.7.1
- djangorestframework==3.12.4
- djoser==2.1.0
- webcolors==1.11.1
- psycopg2-binary==2.9.3
- Pillow==9.0.0
- pytest==6.2.4
- pytest-django==4.4.0
- pytest-pythonpath==0.7.3
- PyJWT==2.9.0
- PyYAML==6.0
- gunicorn==20.1.0
- node.js
- Docker

# Чтобы развернуть проект:
Установите docker compose.
На свой сервер скопируйте файл docker-compose.production.yml, создайте файл .env и заполните его в соответствии с файлом env.example и запустите проект в режиме демона командой ```sudo docker compose -f docker-compose.production.yml up -d```.
Выполните миграции и соберите статику бэкенда, скопируйте её в папку  /static/static/

# Загрузить данные из csv-файлов:
Разместите csv-файлы в каталоге "foodgram\backend\data" или измените путь "PATH_FOR_CSV" к каталогу в файле "foodgram\foodgram\settings.py"
В каталоге с файлом "manage.py" запустить скрипт командой:
```python manage.py csv_loader```


# Для использования CI/CD
В GitHub Actions добавьте следующие секреты:
- NICK - Никнейм на докерхабе
- DOCKER_USERNAME - логин на докерхабе
- DOCKER_PASSWORD - пароль на докерхабе
- HOST - адрес сервера
- USER - имя пользователя на сервере
- SSH_KEY - закрытый ssh-ключ
- SSH_PASSPHRASE - пароль для ssh-ключа
- TELEGRAM_TO - ваш телеграмм id
- TELEGRAM_TOKEN - токен вашего телеграмм-бота


Автор [Анатолий Пономарев](https://github.com/Karramb)