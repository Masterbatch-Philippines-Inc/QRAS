
<div align="center">

  # QRAS

  A web-based attendance management system built for daily use by department head and admin staff. Employees clock in and out using a QR code scanner or by entering their employee ID on a number pad. The system automatically computes hours worked, detects late arrivals, halfdays, undertime, and overtime, and routes records through an approval workflow.

</div>

<br/>


## 1. Setup and Installation

### Requirements
- Python 3.12+
- Django 6.x
- PostgreSQL 16+

### Installation Steps

```bash
# 1. Clone the repo
git clone https://github.com/Masterbatch-Philippines-Inc/QRAS.git

# 2. Create and activate virtual environment
un venv

# 2. Create and activate virtual environment
.venv\Scripts\activate

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Hover to the core app
copy .env.example .env

# 5. Set up environment variables
# Create a .env file and set:
notepad .env

# 6. Regenerate migration files fresh for every app
python manage.py makemigrations qras

# 7. Apply them to the database
python manage.py migrate
```
