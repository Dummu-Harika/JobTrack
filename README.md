# JobTrack — Job Application Tracker

JobTrack is a web-based job application management system built with Flask and PostgreSQL. It helps job seekers organize applications, track recruitment progress, manage follow-up dates, and analyze their job search activity from a centralized dashboard.

## Features

- **User Authentication:** Register, log in, log out, update profile information, and change passwords.
- **Application Management:** Add, view, edit, and delete job applications.
- **Application Status Tracking:** Track applications through Applied, Assessment, Interview, Offer, and Rejected stages.
- **Search and Filtering:** Find applications by search term and filter by application status.
- **Sorting and Pagination:** Sort application records and browse them across pages.
- **Dashboard Analytics:** View application statistics, status distribution, and monthly application trends.
- **Follow-up Reminders:** Identify overdue and upcoming follow-ups.
- **CSV Export:** Export filtered application records for reporting and analysis.
- **Activity History:** Review recent account activity.
- **Security Measures:** Password hashing, CSRF protection, rate limiting, and user-specific data access.
- **Automated Testing:** Test application routes, authentication, data access, and application management.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL |
| ORM | Flask-SQLAlchemy, SQLAlchemy |
| Database Migrations | Flask-Migrate, Alembic |
| Frontend | HTML, CSS, Jinja2 templates |
| Authentication | Werkzeug password hashing, Flask sessions |
| Security | Flask-WTF CSRF protection, Flask-Limiter |
| Testing | pytest |
| Version Control | Git and GitHub |

## Project Structure

```text
JobTrack/
├── app.py
├── config.py
├── extensions.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── application.py
│   └── activity.py
├── migrations/
├── templates/
├── static/
│   └── css/
│       └── style.css
├── tests/
│   ├── conftest.py
│   └── test_app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.12 or a compatible Python version
- PostgreSQL
- Git

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Dummu-Harika/JobTrack.git
cd JobTrack
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root. Set the following variables using your own values:

```env
SECRET_KEY=replace_with_a_long_random_secret
DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/jobtrack_db
```

Replace the database username and password with your PostgreSQL credentials. Create the `jobtrack_db` database before starting the application.

**Security:** Never commit `.env` or real credentials to GitHub. Use a separate test database when running automated tests.

### 5. Apply database migrations

```powershell
flask --app app db upgrade
```

### 6. Start the application

```powershell
flask --app app run
```

Open the local URL displayed in the terminal, usually:

`http://127.0.0.1:5000`

Register an account to begin tracking job applications.

## Running Automated Tests

Configure `TEST_DATABASE_URL` in your local environment to point to the dedicated `jobtrack_test_db` PostgreSQL database. Never point it to your real application database.

Run the test suite with:

```powershell
python -m pytest -v
```

The project includes tests for authentication, application management, access control, searching, filtering, sorting, pagination, and other application behavior.

## Database Safety

- Keep development, test, and production databases separate.
- Apply schema changes through database migrations.
- Never commit database backups, passwords, secret keys, or other sensitive configuration.
- Back up important production data before making schema changes.

## Future Improvements

Potential enhancements include:

- Public cloud deployment
- Automated reminders and notifications
- Job application status timelines
- Resume and job-description matching
- More advanced analytics and reporting

## Author

**Harika Dummu**

GitHub: [Dummu-Harika](https://github.com/Dummu-Harika)

Project repository: [JobTrack](https://github.com/Dummu-Harika/JobTrack)
