# 🚗 CarMarket Pro

REST API маркетплейса автомобилей на Django + DRF.

**Стек:** Django 5 · Django REST Framework · SimpleJWT · django-filter · drf-spectacular (Swagger) · PostgreSQL · Docker · Gunicorn · WhiteNoise

## Возможности

- Регистрация / вход по JWT (access + refresh, logout через blacklist)
- Профиль пользователя (аватар, телефон, город), публичный профиль продавца
- Объявления: марка / модель / год / цена / пробег / топливо / КПП / кузов / город
- Несколько фото на объявление (до 20), загрузка сразу при создании или отдельно
- Поиск, фильтры и сортировка
- Избранное ❤️
- Комментарии
- Чат покупатель ↔ продавец (диалог на каждое объявление, счётчик непрочитанных)
- Статистика объявления: просмотры (уникальные за день), график за 30 дней, избранное, комментарии, чаты
- Django Admin с превью фото и inline-редактированием
- Swagger UI / ReDoc

## Быстрый старт

### Docker (PostgreSQL)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000/api/
- Swagger: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/ (логин/пароль из `.env`: `DJANGO_SUPERUSER_*`)

При старте контейнер сам применяет миграции, заполняет справочник марок (`seed_brands`) и создаёт суперпользователя.

### Локально без Docker (SQLite)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_brands
python manage.py createsuperuser
python manage.py runserver
```

Чтобы работать с PostgreSQL локально, укажите `DATABASE_URL` в `.env`.

### Тесты

```bash
python manage.py test
```

## API

| Метод | URL | Описание |
|---|---|---|
| POST | `/api/auth/register/` | Регистрация (возвращает токены) |
| POST | `/api/auth/login/` | Получить `access` / `refresh` |
| POST | `/api/auth/token/refresh/` | Обновить access |
| POST | `/api/auth/logout/` | Выход (refresh → blacklist) |
| GET/PATCH | `/api/auth/me/` | Мой профиль |
| POST | `/api/auth/me/password/` | Смена пароля |
| GET | `/api/auth/users/{id}/` | Публичный профиль |
| GET | `/api/brands/` | Марки с моделями |
| GET | `/api/models/?brand={id}` | Модели марки |
| GET/POST | `/api/listings/` | Список / создание объявления |
| GET/PATCH/DELETE | `/api/listings/{id}/` | Объявление |
| GET | `/api/listings/my/` | Мои объявления |
| POST | `/api/listings/{id}/photos/` | Загрузить фото (multipart, `images` × N) |
| DELETE | `/api/listings/{id}/photos/{photo_id}/` | Удалить фото |
| POST/DELETE | `/api/listings/{id}/favorite/` | В избранное / убрать |
| GET | `/api/favorites/` | Моё избранное |
| GET/POST | `/api/listings/{id}/comments/` | Комментарии |
| PATCH/DELETE | `/api/comments/{id}/` | Свой комментарий |
| GET | `/api/listings/{id}/stats/` | Статистика (только владелец) |
| GET/POST | `/api/chats/` | Мои диалоги / начать диалог `{listing, text}` |
| GET/POST | `/api/chats/{id}/messages/` | Сообщения (`?after=<id>` для polling) |
| GET | `/api/chats/unread/` | Число непрочитанных |

Авторизация: заголовок `Authorization: Bearer <access>`.

### Фильтры объявлений

```
/api/listings/?brand=2&car_model=5&price_min=5000&price_max=20000
             &year_min=2018&year_max=2023&mileage_max=100000
             &fuel_type=petrol&transmission=automatic&body_type=suv
             &city=Ташкент&has_photos=true&search=camry&ordering=-price
```

`ordering`: `price`, `year`, `mileage`, `created_at`, `views_count` (с `-` — по убыванию).

### Создание объявления с фото

```bash
curl -X POST http://localhost:8000/api/listings/ \
  -H "Authorization: Bearer $TOKEN" \
  -F brand=1 -F car_model=3 -F year=2020 -F price=18500 -F mileage=45000 \
  -F fuel_type=petrol -F transmission=automatic -F city=Ташкент \
  -F images=@front.jpg -F images=@back.jpg -F images=@salon.jpg
```

## Деплой

### Render

1. Залейте проект в GitHub.
2. Render → **New → Blueprint** → выберите репозиторий. `render.yaml` создаст PostgreSQL и web-сервис (Docker).
3. Задайте `DJANGO_SUPERUSER_USERNAME / EMAIL / PASSWORD` в настройках сервиса.

Хост Render (`RENDER_EXTERNAL_HOSTNAME`) добавляется в `ALLOWED_HOSTS` автоматически.

### Railway

1. **New Project → Deploy from GitHub repo** (сборка по `Dockerfile`, см. `railway.json`).
2. Добавьте плагин **PostgreSQL** и в web-сервисе задайте `DATABASE_URL=${{Postgres.DATABASE_URL}}`.
3. Переменные: `SECRET_KEY`, `DEBUG=False`, `DJANGO_SUPERUSER_*`.
4. Settings → Networking → **Generate Domain** (домен попадёт в `ALLOWED_HOSTS` автоматически).

> ⚠️ Файловая система на бесплатных тарифах Render/Railway не постоянная — загруженные фото пропадут при редеплое. Для продакшена подключите S3 / Cloudinary (`django-storages`) или Railway Volume, смонтированный в `/app/media`.

## Структура

```
config/     настройки, корневые urls
users/      кастомный User, регистрация, JWT, профиль
listings/   марки, модели, объявления, фото, избранное, комментарии, статистика
chat/       диалоги и сообщения
```
