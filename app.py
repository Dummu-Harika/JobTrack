
import csv
import io
import math
from datetime import date
from functools import wraps
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    make_response,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, case, or_
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from config import Config
from extensions import db
from models.user import User
from models.application import Application
from models.activity import Activity


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

if not app.config.get("SECRET_KEY"):
    raise RuntimeError(
        "SECRET_KEY is missing. Set it in your environment or .env file."
    )

if not app.config.get("SQLALCHEMY_DATABASE_URI"):
    raise RuntimeError(
        "SQLALCHEMY_DATABASE_URI is missing. Check your Config and .env file."
    )

db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


# =========================================================
# CONSTANTS
# =========================================================

VALID_STATUSES = [
    "Applied",
    "Assessment",
    "Interview",
    "Offer",
    "Rejected",
]

CLOSED_STATUSES = ["Offer", "Rejected"]

SORT_FIELDS = {
    "company_name",
    "job_role",
    "application_date",
    "package_lpa",
    "status",
    "created_at",
}


# =========================================================
# AUTHENTICATION HELPERS
# =========================================================

def login_required(view_function):
    """Allow access only to logged-in users."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# =========================================================
# ACTIVITY HELPER
# =========================================================

def record_activity(user_id, application_id, action, description):
    """Add an activity to the current database transaction."""

    activity = Activity(
        user_id=user_id,
        application_id=application_id,
        action=action,
        description=description,
    )

    db.session.add(activity)


# =========================================================
# FORM VALIDATION HELPERS
# =========================================================

def parse_optional_date(value):
    """Convert an optional YYYY-MM-DD string into a date."""

    value = (value or "").strip()

    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_optional_package(value):
    """Convert an optional package value into a non-negative float."""

    value = (value or "").strip()

    if not value:
        return None

    try:
        package = float(value)
    except ValueError:
        return None

    if not math.isfinite(package) or package < 0:
        return None

    return package


def validate_application_form(form):
    """Validate application form fields and return errors and values."""

    errors = []

    company_name = (form.get("company_name") or "").strip()
    job_role = (form.get("job_role") or "").strip()
    location = (form.get("location") or "").strip()
    status = (form.get("status") or "Applied").strip()
    job_url = (form.get("job_url") or "").strip()
    notes = (form.get("notes") or "").strip()

    application_date_input = (
        form.get("application_date") or ""
    ).strip()

    follow_up_date_input = (
        form.get("follow_up_date") or ""
    ).strip()

    package_input = (form.get("package_lpa") or "").strip()

    if not company_name:
        errors.append("Company name is required.")
    elif len(company_name) > 150:
        errors.append("Company name cannot exceed 150 characters.")

    if not job_role:
        errors.append("Job role is required.")
    elif len(job_role) > 150:
        errors.append("Job role cannot exceed 150 characters.")

    if len(location) > 200:
        errors.append("Location cannot exceed 200 characters.")

    if len(notes) > 10000:
        errors.append("Notes cannot exceed 10,000 characters.")

    if status not in VALID_STATUSES:
        errors.append("Please select a valid application status.")

    package_lpa = None

    if package_input:
        package_lpa = parse_optional_package(package_input)

        if package_lpa is None:
            errors.append(
                "Package must be a valid, non-negative number."
            )

    application_date = None
    follow_up_date = None

    if application_date_input:
        application_date = parse_optional_date(
            application_date_input
        )

        if application_date is None:
            errors.append("Please enter a valid application date.")

    if follow_up_date_input:
        follow_up_date = parse_optional_date(
            follow_up_date_input
        )

        if follow_up_date is None:
            errors.append("Please enter a valid follow-up date.")

    if job_url:
        if len(job_url) > 2048:
            errors.append("Job URL is too long.")
        else:
            parsed_url = urlparse(job_url)

            if (
                parsed_url.scheme not in ("http", "https")
                or not parsed_url.netloc
                or any(char.isspace() for char in job_url)
            ):
                errors.append(
                    "Enter a valid job URL beginning with "
                    "http:// or https://."
                )

    values = {
        "company_name": company_name,
        "job_role": job_role,
        "package_lpa": package_lpa,
        "location": location or None,
        "application_date": application_date,
        "follow_up_date": follow_up_date,
        "status": status,
        "job_url": job_url or None,
        "notes": notes or None,
    }

    return errors, values


# =========================================================
# APPLICATION SEARCH, FILTERING AND SORTING
# =========================================================

def get_filtered_applications(user_id, search_query, status_filter):
    """Build a database query for this user's filtered applications."""

    query = Application.query.filter_by(user_id=user_id)

    if search_query:
        search_pattern = f"%{search_query}%"

        query = query.filter(
            or_(
                Application.company_name.ilike(search_pattern),
                Application.job_role.ilike(search_pattern),
            )
        )

    if status_filter in VALID_STATUSES:
        query = query.filter(
            Application.status == status_filter
        )

    return query


def sort_applications(query, sort_by, sort_order):
    """Apply database sorting using an allowlist of fields."""

    if sort_by not in SORT_FIELDS:
        sort_by = "created_at"

    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    sort_column = getattr(Application, sort_by)

    if sort_order == "asc":
        query = query.order_by(
            sort_column.asc().nullslast(),
            Application.id.asc(),
        )
    else:
        query = query.order_by(
            sort_column.desc().nullslast(),
            Application.id.desc(),
        )

    return query, sort_by, sort_order


def csv_safe_value(value):
    """Reduce spreadsheet formula-injection risk in exported text."""

    if value is None:
        return ""

    value = str(value)

    if value.lstrip().startswith(
        ("=", "+", "-", "@", "\t", "\r")
    ):
        return "'" + value

    return value


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("applications"))

    return render_template("home.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if "user_id" in session:
        return redirect(url_for("applications"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (
            request.form.get("email") or ""
        ).strip().lower()
        password = request.form.get("password") or ""
        confirm_password = (
            request.form.get("confirm_password") or ""
        )

        errors = []

        if not name:
            errors.append("Name is required.")
        elif len(name) > 100:
            errors.append("Name cannot exceed 100 characters.")

        if (
            not email
            or len(email) > 120
            or "@" not in email
            or email.startswith("@")
            or email.endswith("@")
            or " " in email
        ):
            errors.append("Enter a valid email address.")

        if len(password) < 8:
            errors.append(
                "Password must contain at least 8 characters."
            )

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if not errors:
            existing_user = User.query.filter_by(
                email=email
            ).first()

            if existing_user:
                errors.append(
                    "An account with this email already exists."
                )

        if errors:
            for error in errors:
                flash(error, "danger")

            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
        )

        try:
            db.session.add(user)
            db.session.commit()

            flash(
                "Registration successful. Please log in.",
                "success",
            )

            return redirect(url_for("login"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Registration failed.")

            flash(
                "Registration could not be completed. Please try again.",
                "danger",
            )

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if "user_id" in session:
        return redirect(url_for("applications"))

    if request.method == "POST":
        email = (
            request.form.get("email") or ""
        ).strip().lower()

        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(
            user.password_hash, password
        ):
            session.clear()
            session.permanent = True
            session["user_id"] = user.id
            session["user_name"] = user.name

            flash(f"Welcome back, {user.name}!", "success")

            return redirect(url_for("applications"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")

    return redirect(url_for("home"))


# =========================================================
# PROFILE MANAGEMENT
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = db.session.get(User, session["user_id"])

    if user is None:
        session.clear()
        flash("Please log in again.", "warning")

        return redirect(url_for("login"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (
            request.form.get("email") or ""
        ).strip().lower()

        errors = []

        if not name:
            errors.append("Name is required.")
        elif len(name) > 120:
            errors.append("Name cannot exceed 120 characters.")

        if (
            not email
            or len(email) > 254
            or "@" not in email
            or email.startswith("@")
            or email.endswith("@")
            or " " in email
        ):
            errors.append("Enter a valid email address.")

        if not errors:
            existing_user = User.query.filter(
                User.email == email,
                User.id != user.id,
            ).first()

            if existing_user:
                errors.append(
                    "This email address is already registered."
                )

        if errors:
            for error in errors:
                flash(error, "danger")

            return render_template("profile.html", user=user)

        try:
            user.name = name
            user.email = email

            db.session.commit()

            session["user_name"] = user.name

            flash("Profile updated successfully.", "success")

            return redirect(url_for("profile"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Profile update failed.")

            flash(
                "Could not update your profile. Please try again.",
                "danger",
            )

    return render_template("profile.html", user=user)


# =========================================================
# CHANGE PASSWORD
# =========================================================

@app.route("/change-password", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per hour")
def change_password():
    user = db.session.get(User, session["user_id"])

    if user is None:
        session.clear()
        flash("Please log in again.", "warning")

        return redirect(url_for("login"))

    if request.method == "POST":
        current_password = (
            request.form.get("current_password") or ""
        )

        new_password = (
            request.form.get("new_password") or ""
        )

        confirm_password = (
            request.form.get("confirm_password") or ""
        )

        errors = []

        if not current_password:
            errors.append("Current password is required.")
        elif not check_password_hash(
            user.password_hash, current_password
        ):
            errors.append("Your current password is incorrect.")

        if len(new_password) < 8:
            errors.append(
                "New password must contain at least 8 characters."
            )

        if new_password != confirm_password:
            errors.append("New passwords do not match.")

        if (
            current_password
            and new_password
            and current_password == new_password
        ):
            errors.append(
                "Your new password must differ from your current password."
            )

        if errors:
            for error in errors:
                flash(error, "danger")

            return render_template("change_password.html")

        try:
            user.password_hash = generate_password_hash(
                new_password
            )

            db.session.commit()

            flash("Password changed successfully.", "success")

            return redirect(url_for("applications"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Password change failed.")

            flash(
                "Could not change your password. Please try again.",
                "danger",
            )

    return render_template("change_password.html")


# =========================================================
# APPLICATION DASHBOARD
# =========================================================

@app.route("/applications")
@login_required
def applications():
    user_id = session["user_id"]
    today = date.today()

    # Recent activity: newest 10 records for this user.
    recent_activities = (
        Activity.query
        .filter_by(user_id=user_id)
        .order_by(
            Activity.created_at.desc(),
            Activity.id.desc(),
        )
        .limit(10)
        .all()
    )

    # All applications for this user are retained for dashboard
    # charts and follow-up reminders.
    user_applications = (
        Application.query
        .filter_by(user_id=user_id)
        .order_by(Application.created_at.desc())
        .all()
    )

    # Dashboard statistics calculated directly in PostgreSQL.
    statistics = (
        db.session.query(
            func.count(Application.id).label("total"),
            func.count(
                case(
                    (Application.status == "Interview", 1)
                )
            ).label("interviews"),
            func.count(
                case(
                    (Application.status == "Offer", 1)
                )
            ).label("offers"),
            func.count(
                case(
                    (Application.status == "Rejected", 1)
                )
            ).label("rejections"),
        )
        .filter(Application.user_id == user_id)
        .one()
    )

    total_applications = statistics.total
    total_interviews = statistics.interviews
    total_offers = statistics.offers
    total_rejections = statistics.rejections

    # Follow-up reminders exclude closed applications.
    active_applications = [
        application
        for application in user_applications
        if application.status not in CLOSED_STATUSES
        and application.follow_up_date is not None
    ]

    overdue_follow_ups = sorted(
        [
            application
            for application in active_applications
            if application.follow_up_date < today
        ],
        key=lambda application: application.follow_up_date,
    )

    upcoming_follow_ups = sorted(
        [
            application
            for application in active_applications
            if application.follow_up_date >= today
        ],
        key=lambda application: application.follow_up_date,
    )

    # Read search and filter values.
    search_query = (
        request.args.get("search") or ""
    ).strip()

    requested_status = (
        request.args.get("status") or ""
    ).strip()

    status_filter = (
        requested_status
        if requested_status in VALID_STATUSES
        else ""
    )

    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")

    # Build the filtered query in PostgreSQL.
    filtered_query = get_filtered_applications(
        user_id,
        search_query,
        status_filter,
    )

    # Sort in PostgreSQL.
    filtered_query, sort_by, sort_order = sort_applications(
        filtered_query,
        sort_by,
        sort_order,
    )

    # Pagination: display 10 applications per page.
    page = request.args.get("page", 1, type=int)
    page = max(page, 1)

    pagination = filtered_query.paginate(
        page=page,
        per_page=10,
        error_out=False,
    )

    filtered_applications = pagination.items

    # Chart 1: applications grouped by status.
    status_counts = {
        status: sum(
            application.status == status
            for application in user_applications
        )
        for status in VALID_STATUSES
    }

    # Chart 2: applications per month for the latest six months.
    monthly_labels = []
    monthly_counts = []

    for offset in range(5, -1, -1):
        month_number = today.month - offset
        year_number = today.year

        while month_number <= 0:
            month_number += 12
            year_number -= 1

        month_start = date(
            year_number,
            month_number,
            1,
        )

        if month_number == 12:
            next_month_start = date(
                year_number + 1,
                1,
                1,
            )
        else:
            next_month_start = date(
                year_number,
                month_number + 1,
                1,
            )

        monthly_count = sum(
            application.application_date is not None
            and month_start <= application.application_date
            < next_month_start
            for application in user_applications
        )

        monthly_labels.append(month_start.strftime("%b %Y"))
        monthly_counts.append(monthly_count)

    return render_template(
        "applications/list.html",
        applications=filtered_applications,
        pagination=pagination,
        total_applications=total_applications,
        total_interviews=total_interviews,
        total_offers=total_offers,
        total_rejections=total_rejections,
        overdue_follow_ups=overdue_follow_ups,
        upcoming_follow_ups=upcoming_follow_ups,
        recent_activities=recent_activities,
        search_query=search_query,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        status_counts=status_counts,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts,
        today=today,
    )


# =========================================================
# EXPORT APPLICATIONS TO CSV
# =========================================================

@app.route("/applications/export")
@login_required
def export_applications():
    user_id = session["user_id"]

    search_query = (
        request.args.get("search") or ""
    ).strip()

    requested_status = (
        request.args.get("status") or ""
    ).strip()

    status_filter = (
        requested_status
        if requested_status in VALID_STATUSES
        else ""
    )

    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")

    export_query = get_filtered_applications(
        user_id,
        search_query,
        status_filter,
    )

    export_query, sort_by, sort_order = sort_applications(
        export_query,
        sort_by,
        sort_order,
    )

    # Export every matching record, not only the current page.
    export_rows = export_query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Company",
        "Job Role",
        "Package (LPA)",
        "Location",
        "Application Date",
        "Follow-up Date",
        "Status",
        "Job URL",
        "Notes",
    ])

    for application in export_rows:
        writer.writerow([
            csv_safe_value(application.company_name),
            csv_safe_value(application.job_role),
            (
                application.package_lpa
                if application.package_lpa is not None
                else ""
            ),
            csv_safe_value(application.location),
            (
                application.application_date.isoformat()
                if application.application_date
                else ""
            ),
            (
                application.follow_up_date.isoformat()
                if application.follow_up_date
                else ""
            ),
            csv_safe_value(application.status),
            csv_safe_value(application.job_url),
            csv_safe_value(application.notes),
        ])

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers[
        "Content-Disposition"
    ] = 'attachment; filename="jobtrack_applications.csv"'
    response.headers["X-Content-Type-Options"] = "nosniff"

    return response


# =========================================================
# ADD APPLICATION
# =========================================================

@app.route("/applications/add", methods=["GET", "POST"])
@login_required
def add_application():
    if request.method == "POST":
        errors, values = validate_application_form(request.form)

        if errors:
            for error in errors:
                flash(error, "danger")

            return render_template("applications/add.html")

        application = Application(
            user_id=session["user_id"],
            **values,
        )

        try:
            db.session.add(application)

            # Generate the ID before recording activity.
            db.session.flush()

            record_activity(
                user_id=session["user_id"],
                application_id=application.id,
                action="created",
                description=(
                    f"Added {application.job_role} at "
                    f"{application.company_name}."
                ),
            )

            # Save the application and activity together.
            db.session.commit()

            flash(
                "Job application added successfully.",
                "success",
            )

            return redirect(url_for("applications"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Adding application failed.")

            flash(
                "Could not save the application. Please try again.",
                "danger",
            )

    return render_template("applications/add.html")


# =========================================================
# EDIT APPLICATION
# =========================================================

@app.route(
    "/applications/edit/<int:application_id>",
    methods=["GET", "POST"],
)
@login_required
def edit_application(application_id):
    application = Application.query.filter_by(
        id=application_id,
        user_id=session["user_id"],
    ).first_or_404()

    if request.method == "POST":
        errors, values = validate_application_form(request.form)

        if errors:
            for error in errors:
                flash(error, "danger")

            return render_template(
                "applications/edit.html",
                application=application,
            )

        # Capture the old status before applying changes.
        old_status = application.status

        for field, value in values.items():
            setattr(application, field, value)

        try:
            if application.status != old_status:
                record_activity(
                    user_id=session["user_id"],
                    application_id=application.id,
                    action="status_changed",
                    description=(
                        f"{application.company_name}: "
                        f"{old_status} → {application.status}."
                    ),
                )
            else:
                record_activity(
                    user_id=session["user_id"],
                    application_id=application.id,
                    action="updated",
                    description=(
                        f"Updated {application.job_role} at "
                        f"{application.company_name}."
                    ),
                )

            db.session.commit()

            flash(
                "Job application updated successfully.",
                "success",
            )

            return redirect(url_for("applications"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Updating application failed.")

            flash(
                "Could not update the application. Please try again.",
                "danger",
            )

    return render_template(
        "applications/edit.html",
        application=application,
    )


# =========================================================
# DELETE APPLICATION
# =========================================================

@app.route(
    "/applications/delete/<int:application_id>",
    methods=["POST"],
)
@login_required
def delete_application(application_id):
    application = Application.query.filter_by(
        id=application_id,
        user_id=session["user_id"],
    ).first_or_404()

    try:
        # Preserve the deletion event after the application is removed.
        record_activity(
            user_id=session["user_id"],
            application_id=None,
            action="deleted",
            description=(
                f"Deleted {application.job_role} at "
                f"{application.company_name}."
            ),
        )

        db.session.delete(application)
        db.session.commit()

        flash(
            "Job application deleted successfully.",
            "success",
        )

    except Exception:
        db.session.rollback()
        app.logger.exception("Deleting application failed.")

        flash(
            "Could not delete the application. Please try again.",
            "danger",
        )

    return redirect(url_for("applications"))


# =========================================================
# RATE LIMIT ERROR
# =========================================================

@app.errorhandler(429)
def rate_limit_exceeded(error):
    flash(
        "Too many requests. Please wait a little and try again.",
        "warning",
    )

    return render_template("429.html"), 429


# =========================================================
# DATABASE INITIALIZATION AND RUN
# =========================================================

if __name__ == "__main__":
    with app.app_context():
        try:
            # Existing tables are preserved. This does not replace
            # Flask-Migrate for future schema changes.
            db.create_all()
            app.logger.info("Database tables are ready.")

        except Exception:
            app.logger.exception(
                "Database initialization failed. Check PostgreSQL "
                "and your database configuration."
            )
            raise

    app.run(debug=True)
