
<div align="center">

  # QRAS

  A web-based attendance management system built for daily use by department head and admin staff. Employees clock in and out using a QR code scanner or by entering their employee ID on a number pad. The system automatically computes hours worked, detects late arrivals, halfdays, undertime, and overtime, and routes records through an approval workflow.

</div>

<br/>


## Setup and Installation

### Requirements
- Python 3.12+
- Django 6.x
- PostgreSQL 16+

### Installation Steps

#### 1. Clone the repo
```bash
git clone https://github.com/Masterbatch-Philippines-Inc/QRAS.git
```
#### 2. Create and activate virtual environment
```bash
uv venv
```
```bash
.venv\Scripts\activate
```
#### 3. Install dependencies
```bash
uv pip install -r requirements.txt
```
#### 4. Create new copy of `.env` file
```bash
copy .env.example .env
```
#### 5. Setup vars in `.env` file
```bash
notepad .env
```
#### 6. Regenerate database tables
```bash
py manage.py makemigrations qras
```

> [!Important]
> Create database in psql first before migrating models.

#### 7. Apply migrations
```bash
py manage.py migrate
```
#### 8. Create new user via Django
```bash
py manage.py createsuperuser
```
#### 9. Run and test the program
```bash
py manage.py runserver
```

### Extras

#### 1. Generate random secret key via python
```bash
py -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
#### 2. Check python bit
```bash
py -c "import struct; print(struct.calcsize('P')*8)"
```
#### 3. Compile the static files
```bash
python manage.py collectstatic --noinput
```
