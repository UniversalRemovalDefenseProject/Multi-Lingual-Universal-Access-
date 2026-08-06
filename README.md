# URDP Intake Platform

Secure, multilingual asylum intake platform for [Universal Removal Defense Project](https://www.universalremovaldefenseproject.org). Built to eliminate language and technology barriers for immigrants facing detention and deportation proceedings.

> Pending DOJ Recognition & Accreditation. Submitting an intake form does not create an attorney-client relationship.

---

## Tech Stack

- **Backend:** Python, Django 6
- **Database:** PostgreSQL 18 (Docker for local dev)
- **Infrastructure:** Docker, DigitalOcean
- **i18n:** Django i18n — 10 languages with RTL support

## Supported Languages

English, Spanish, French, Arabic, Haitian Creole, Russian, Hindi, Punjabi, Portuguese, Chinese (Simplified)

---

## Local Development

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker + Colima.

```bash
git clone https://github.com/UniversalRemovalDefenseProject/Multi-Lingual-Universal-Access-.git
cd Multi-Lingual-Universal-Access-
cp .env.example .env    # Windows: copy .env.example .env
docker-compose up --build
```

Fill in `SECRET_KEY` and `POSTGRES_PASSWORD` in `.env` before starting. The key
generation command is in `.env.example`. All other defaults work as-is.

Visit `http://localhost:8000/asylum-intake/` for the intake form and `http://localhost:8000/admin` for the admin dashboard.

**Create an admin account:**

```bash
docker-compose exec web python manage.py createsuperuser
```

### Without Docker

You'll need a local PostgreSQL 18 instance and `gettext` on your PATH. Set
`POSTGRES_HOST=localhost` in your `.env` and point the other `POSTGRES_*`
variables at your instance.

Django reads compiled `.mo` files, and those are gitignored — so `compilemessages` must run
before the server, or the form serves English only.

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py compilemessages --ignore='*/site-packages/*'
python manage.py runserver
```

Run `compilemessages` before `python manage.py test` too — the test suite asserts on translated
output. The Docker paths handle this for you via `entrypoint.sh`.

---

## Project Structure

```
intake/          # Intake form app — models, views, forms, templates
urdp/            # Django project settings and URL config
locale/          # Translation files (.po) for all supported languages
```

---

## Contributing

We welcome developers, designers, and multilingual contributors. See the [wiki](../../wiki) for the full roadmap and contribution guidelines.

Open issues are a good place to start.

---

## Disclaimer

This platform is under active development and is not a production legal-services system. URDP does not provide legal representation through this repository. Representation may only begin after formal intake review, conflict screening, and written acceptance.
