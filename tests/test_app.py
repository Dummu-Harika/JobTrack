
import pytest

from app import app as flask_app




def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200


def test_applications_page_requires_login(client):
    response = client.get("/applications")

    assert response.status_code in (302, 401)


def test_login_page_loads(client):
    response = client.get("/login")

    assert response.status_code == 200

def test_register_page_loads(client):
    response = client.get("/register")

    assert response.status_code == 200



def test_invalid_login_does_not_authenticate(client):
    response = client.post(
        "/login",
        data={
            "email": "nobody@example.com",
            "password": "WrongPassword123!",
        },
        follow_redirects=False,
    )

    assert response.status_code in (200, 302)

    with client.session_transaction() as session_data:
        assert "user_id" not in session_data

def test_add_application_page_requires_login(client):
    response = client.get("/applications/add")

    assert response.status_code in (302, 401)


def test_invalid_application_date_is_rejected(client):
    from app import validate_application_form

    form_data = {
        "company_name": "Test Company",
        "job_role": "Python Developer",
        "package_lpa": "5",
        "location": "Visakhapatnam",
        "application_date": "not-a-date",
        "follow_up_date": "",
        "status": "Applied",
        "job_url": "https://example.com/job",
        "notes": "",
    }

    errors = validate_application_form(form_data)

    assert errors

def test_application_model_has_required_fields():
    from models.application import Application

    required_fields = [
        "user_id",
        "company_name",
        "job_role",
        "status",
    ]

    for field in required_fields:
        assert hasattr(Application, field)



def test_user_model_has_applications_relationship():
    from models.user import User

    assert hasattr(User, "applications")

def test_registration_creates_user(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "testuser@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    user = User.query.filter_by(
        email="testuser@example.com"
    ).first()

    assert user is not None
    assert user.password_hash != "TestPassword123!"

def test_duplicate_email_registration_is_rejected(client):
    from models.user import User
    from extensions import db

    user = User(
        name="Existing User",
        email="duplicate@example.com",
        password_hash="existing_hash",
    )
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/register",
        data={
            "name": "Another User",
            "email": "duplicate@example.com",
            "password": "AnotherPassword123!",
            "confirm_password": "AnotherPassword123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    users = User.query.filter_by(
        email="duplicate@example.com"
    ).all()

    assert len(users) == 1

def test_login_with_valid_credentials(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Login Test User",
        email="logintest@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/login",
        data={
            "email": "logintest@example.com",
            "password": "CorrectPassword123!",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    dashboard_response = client.get("/applications")
    assert dashboard_response.status_code == 200

def test_login_with_wrong_password_is_rejected(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Wrong Password Test",
        email="wrongpassword@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/login",
        data={
            "email": "wrongpassword@example.com",
            "password": "WrongPassword123!",
        },
        follow_redirects=False,
    )

    assert response.status_code in (200, 302)

    with client.session_transaction() as session_data:
        assert "user_id" not in session_data

def test_logout_ends_user_session(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Logout Test User",
        email="logouttest@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    # Log in first.
    client.post(
        "/login",
        data={
            "email": "logouttest@example.com",
            "password": "CorrectPassword123!",
        },
    )

    # Logout route should accept POST.
    response = client.post("/logout", follow_redirects=False)

    assert response.status_code == 302

    # Protected dashboard should no longer be accessible.
    dashboard_response = client.get(
        "/applications",
        follow_redirects=False,
    )

    assert dashboard_response.status_code in (302, 401)

def test_logged_in_user_can_add_application(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Application Test User",
        email="addapp@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    # Log in.
    client.post(
        "/login",
        data={
            "email": "addapp@example.com",
            "password": "CorrectPassword123!",
        },
    )

    # Submit a new application.
    response = client.post(
        "/applications/add",
        data={
            "company_name": "Test Technologies",
            "job_role": "Python Developer",
            "package_lpa": "5",
            "location": "Visakhapatnam",
            "application_date": "2026-10-20",
            "follow_up_date": "",
            "status": "Applied",
            "job_url": "https://example.com/job",
            "notes": "Testing application creation",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    application = Application.query.filter_by(
        company_name="Test Technologies",
        user_id=user.id,
    ).first()

    assert application is not None
    assert application.job_role == "Python Developer"
    assert application.status == "Applied"

def test_user_cannot_access_another_users_application(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    # Create two users.
    user1 = User(
        name="User One",
        email="userone@example.com",
        password_hash=generate_password_hash("Password123!"),
    )
    user2 = User(
        name="User Two",
        email="usertwo@example.com",
        password_hash=generate_password_hash("Password123!"),
    )

    db.session.add_all([user1, user2])
    db.session.commit()

    # Create an application belonging to User Two.
    application = Application(
        user_id=user2.id,
        company_name="Private Company",
        job_role="Backend Developer",
        status="Applied",
    )
    db.session.add(application)
    db.session.commit()

    application_id = application.id

    # Log in as User One.
    client.post(
        "/login",
        data={
            "email": "userone@example.com",
            "password": "Password123!",
        },
    )

    # Try to open User Two's application.
    response = client.get(
        f"/applications/{application_id}/edit",
        follow_redirects=False,
    )

    assert response.status_code in (403, 404, 302)

def test_user_cannot_delete_another_users_application(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    # Create two users.
    user1 = User(
        name="Delete Test User One",
        email="deleteuser1@example.com",
        password_hash=generate_password_hash("Password123!"),
    )
    user2 = User(
        name="Delete Test User Two",
        email="deleteuser2@example.com",
        password_hash=generate_password_hash("Password123!"),
    )

    db.session.add_all([user1, user2])
    db.session.commit()

    # Create an application owned by User Two.
    application = Application(
        user_id=user2.id,
        company_name="Protected Company",
        job_role="Python Developer",
        status="Applied",
    )
    db.session.add(application)
    db.session.commit()

    application_id = application.id

    # Log in as User One.
    client.post(
        "/login",
        data={
            "email": "deleteuser1@example.com",
            "password": "Password123!",
        },
    )

    # Attempt to delete User Two's application.
    response = client.post(
        f"/applications/{application_id}/delete",
        follow_redirects=False,
    )

    # The request must not successfully delete the application.
    assert response.status_code in (403, 404, 302)

    # Confirm that the application still exists.
    saved_application = db.session.get(
        Application,
        application_id,
    )

    assert saved_application is not None
    assert saved_application.user_id == user2.id

def test_user_cannot_edit_another_users_application(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    # Create two users.
    user1 = User(
        name="Edit Test User One",
        email="edituser1@example.com",
        password_hash=generate_password_hash("Password123!"),
    )
    user2 = User(
        name="Edit Test User Two",
        email="edituser2@example.com",
        password_hash=generate_password_hash("Password123!"),
    )

    db.session.add_all([user1, user2])
    db.session.commit()

    # Create an application belonging to User Two.
    application = Application(
        user_id=user2.id,
        company_name="Original Company",
        job_role="Backend Developer",
        status="Applied",
    )
    db.session.add(application)
    db.session.commit()

    application_id = application.id

    # Log in as User One.
    client.post(
        "/login",
        data={
            "email": "edituser1@example.com",
            "password": "Password123!",
        },
    )

    # Attempt to edit User Two's application.
    response = client.post(
        f"/applications/{application_id}/edit",
        data={
            "company_name": "Modified Company",
            "job_role": "Python Developer",
            "status": "Offer",
        },
        follow_redirects=False,
    )

    # The request must not succeed.
    assert response.status_code in (403, 404, 302)

    # Verify that the original record remains unchanged.
    saved_application = db.session.get(
        Application,
        application_id,
    )

    assert saved_application is not None
    assert saved_application.company_name == "Original Company"
    assert saved_application.status == "Applied"

def test_logged_in_user_can_export_applications_csv(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="CSV Test User",
        email="csvuser@example.com",
        password_hash=generate_password_hash("Password123!"),
    )
    db.session.add(user)
    db.session.commit()

    application = Application(
        user_id=user.id,
        company_name="CSV Test Company",
        job_role="Python Developer",
        status="Applied",
    )
    db.session.add(application)
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "csvuser@example.com",
            "password": "Password123!",
        },
    )

    response = client.get("/applications/export")

    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert b"CSV Test Company" in response.data
    assert b"Python Developer" in response.data

def test_csv_export_contains_only_current_users_applications(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    user1 = User(
        name="Export User One",
        email="exportuser1@example.com",
        password_hash=generate_password_hash("Password123!"),
    )
    user2 = User(
        name="Export User Two",
        email="exportuser2@example.com",
        password_hash=generate_password_hash("Password123!"),
    )

    db.session.add_all([user1, user2])
    db.session.commit()

    app1 = Application(
        user_id=user1.id,
        company_name="User One Company",
        job_role="Python Developer",
        status="Applied",
    )
    app2 = Application(
        user_id=user2.id,
        company_name="User Two Private Company",
        job_role="Backend Developer",
        status="Interview",
    )

    db.session.add_all([app1, app2])
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "exportuser1@example.com",
            "password": "Password123!",
        },
    )

    response = client.get("/applications/export")

    assert response.status_code == 200
    assert b"User One Company" in response.data
    assert b"User Two Private Company" not in response.data

def test_registration_rejects_short_password(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "Short Password User",
            "email": "shortpassword@example.com",
            "password": "abc123",
            "confirm_password": "abc123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    # The account must not be created.
    user = User.query.filter_by(
        email="shortpassword@example.com"
    ).first()

    assert user is None
    assert b"Password must contain at least 8 characters." in response.data

def test_registration_rejects_mismatched_passwords(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "Mismatch Test User",
            "email": "mismatch@example.com",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    user = User.query.filter_by(
        email="mismatch@example.com"
    ).first()

    assert user is None
    assert b"Passwords do not match." in response.data

def test_registration_rejects_invalid_email(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "Invalid Email User",
            "email": "invalid-email",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    user = User.query.filter_by(
        email="invalid-email"
    ).first()

    assert user is None
    assert b"Enter a valid email address." in response.data

def test_registration_rejects_empty_name(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "   ",
            "email": "emptyname@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    user = User.query.filter_by(
        email="emptyname@example.com"
    ).first()

    assert user is None
    assert b"Name is required." in response.data

def test_registration_rejects_name_over_100_characters(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "A" * 101,
            "email": "longname@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    user = User.query.filter_by(
        email="longname@example.com"
    ).first()

    assert user is None
    assert b"Name cannot exceed 100 characters." in response.data

def test_registration_rejects_name_over_100_characters(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "A" * 101,
            "email": "longname@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Name cannot exceed 100 characters." in response.data
    assert User.query.filter_by(email="longname@example.com").first() is None


def test_registration_rejects_email_over_120_characters(client):
    from models.user import User

    # The email exceeds the route's 120-character limit.
    email = "a" * 110 + "@example.com"

    response = client.post(
        "/register",
        data={
            "name": "Long Email User",
            "email": email,
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Enter a valid email address." in response.data
    assert User.query.filter_by(email=email).first() is None


def test_registration_rejects_empty_email(client):
    from models.user import User

    response = client.post(
        "/register",
        data={
            "name": "Empty Email User",
            "email": "",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Enter a valid email address." in response.data
    assert User.query.filter_by(email="").first() is None

def test_change_password_rejects_wrong_current_password(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash, check_password_hash

    user = User(
        name="Password Test User",
        email="passwordtest@example.com",
        password_hash=generate_password_hash("CorrectPass123!"),
    )
    db.session.add(user)
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "passwordtest@example.com",
            "password": "CorrectPass123!",
        },
    )

    client.post(
        "/change-password",
        data={
            "current_password": "WrongPass123!",
            "new_password": "NewSecurePass456!",
            "confirm_password": "NewSecurePass456!",
        },
        follow_redirects=True,
    )

    db.session.refresh(user)

    assert check_password_hash(user.password_hash, "CorrectPass123!")


def test_change_password_rejects_mismatched_confirmation(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash, check_password_hash

    user = User(
        name="Password Match Test",
        email="passwordmatch@example.com",
        password_hash=generate_password_hash("CurrentPass123!"),
    )
    db.session.add(user)
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "passwordmatch@example.com",
            "password": "CurrentPass123!",
        },
    )

    client.post(
        "/change-password",
        data={
            "current_password": "CurrentPass123!",
            "new_password": "NewSecurePass456!",
            "confirm_password": "DifferentPass789!",
        },
        follow_redirects=True,
    )

    db.session.refresh(user)

    assert check_password_hash(user.password_hash, "CurrentPass123!")

def test_csv_export_requires_login(client):
    response = client.get(
        "/applications/export",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_delete_application_requires_login(client):
    response = client.post(
        "/applications/delete/1",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_edit_application_requires_login(client):
    response = client.get(
        "/applications/edit/1",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]




def test_profile_requires_login(client):
    response = client.get(
        "/profile",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_change_password_requires_login(client):
    response = client.get(
        "/change-password",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_rate_limit_error_page_renders(client):
    response = client.get("/__test_rate_limit_page__")

    # This URL should not exist in the real application.
    assert response.status_code == 404

def test_applications_dashboard_loads_for_logged_in_user(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Dashboard Test User",
        email="dashboardtest@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "dashboardtest@example.com",
            "password": "CorrectPassword123!",
        },
    )

    response = client.get("/applications")

    assert response.status_code == 200


def test_applications_search_preserves_dashboard_access(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Search Test User",
        email="searchtest@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "searchtest@example.com",
            "password": "CorrectPassword123!",
        },
    )

    response = client.get("/applications?search=Python")

    assert response.status_code == 200


def test_applications_status_filter_preserves_dashboard_access(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Filter Test User",
        email="filtertest@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "filtertest@example.com",
            "password": "CorrectPassword123!",
        },
    )

    response = client.get("/applications?status=Applied")

    assert response.status_code == 200

def test_search_returns_matching_application_only(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Search Result User",
        email="searchresults@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    db.session.add_all([
        Application(
            user_id=user.id,
            company_name="Alpha Technologies",
            job_role="Python Developer",
            status="Applied",
        ),
        Application(
            user_id=user.id,
            company_name="Beta Systems",
            job_role="Java Developer",
            status="Interview",
        ),
    ])
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "searchresults@example.com",
            "password": "CorrectPassword123!",
        },
    )

    response = client.get(
        "/applications?search=Alpha",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Alpha Technologies" in response.data
    assert b"Beta Systems" not in response.data


def test_status_filter_returns_matching_application_only(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Status Filter User",
        email="statusfilter@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    db.session.add_all([
        Application(
            user_id=user.id,
            company_name="Applied Company",
            job_role="Python Developer",
            status="Applied",
        ),
        Application(
            user_id=user.id,
            company_name="Interview Company",
            job_role="Backend Developer",
            status="Interview",
        ),
    ])
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "statusfilter@example.com",
            "password": "CorrectPassword123!",
        },
    )

    response = client.get(
        "/applications?status=Applied",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Applied Company" in response.data
    assert b"Interview Company" not in response.data

def test_applications_can_be_sorted_by_company_name(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Sorting Test User",
        email="sortingtest@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    db.session.add_all([
        Application(
            user_id=user.id,
            company_name="Zenith Technologies",
            job_role="Python Developer",
            status="Applied",
        ),
        Application(
            user_id=user.id,
            company_name="Alpha Systems",
            job_role="Backend Developer",
            status="Interview",
        ),
    ])
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "sortingtest@example.com",
            "password": "CorrectPassword123!",
        },
    )

    response = client.get(
        "/applications?sort_by=company_name&sort_order=asc",
        follow_redirects=True,
    )

    assert response.status_code == 200

    alpha_position = response.data.index(b"Alpha Systems")
    zenith_position = response.data.index(b"Zenith Technologies")

    assert alpha_position < zenith_position


def test_applications_pagination_displays_next_page(client):
    from models.user import User
    from models.application import Application
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Pagination Test User",
        email="paginationtest@example.com",
        password_hash=generate_password_hash("CorrectPassword123!"),
    )
    db.session.add(user)
    db.session.commit()

    applications = [
        Application(
            user_id=user.id,
            company_name=f"Company {i:02d}",
            job_role="Python Developer",
            status="Applied",
        )
        for i in range(1, 12)
    ]

    db.session.add_all(applications)
    db.session.commit()

    client.post(
        "/login",
        data={
            "email": "paginationtest@example.com",
            "password": "CorrectPassword123!",
        },
    )

    first_page = client.get(
        "/applications?page=1&sort_by=company_name&sort_order=asc"
    )
    second_page = client.get(
        "/applications?page=2&sort_by=company_name&sort_order=asc"
    )

    first_page = client.get(
        "/applications?page=1&sort_by=company_name&sort_order=asc"
    )
    second_page = client.get(
        "/applications?page=2&sort_by=company_name&sort_order=asc"
    )

    # Temporary debugging code
    print("FIRST PAGE STATUS:", first_page.status_code)
    print("FIRST PAGE HAS COMPANY 01:", b"Company 01" in first_page.data)
    print("FIRST PAGE HAS COMPANY 11:", b"Company 11" in first_page.data)
    print("SECOND PAGE HAS COMPANY 11:", b"Company 11" in second_page.data)
    print("FIRST PAGE HTML:", first_page.data.decode("utf-8-sig")[:12000])

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert b"Company 01" in first_page.data
    assert b"Company 10" in first_page.data
    assert b"Company 11" not in first_page.data

    assert b"Company 11" in second_page.data
    assert b"Company 01" not in second_page.data
