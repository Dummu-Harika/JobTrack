
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app import app as flask_app
from extensions import db


@pytest.fixture(scope="session", autouse=True)
def test_database():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.fail(
            "Set TEST_DATABASE_URL to the jobtrack_test_db database."
        )

    if make_url(database_url).database != "jobtrack_test_db":
        pytest.fail("Tests may only use jobtrack_test_db.")

    original_database_uri = flask_app.config[
        "SQLALCHEMY_DATABASE_URI"
    ]

    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=database_url,
    )

    try:
        with flask_app.app_context():
            engines = db.engines
            original_engine = engines[None]

            test_engine = create_engine(
                database_url,
                pool_pre_ping=True,
            )

            # Route database operations to the test database.
            engines[None] = test_engine
            database_created = False

            try:
                actual_db_name = db.engine.url.database

                if actual_db_name != "jobtrack_test_db":
                    pytest.fail(
                        f"Safety check failed: connected to "
                        f"{actual_db_name!r}. No tables were changed."
                    )

                db.create_all()
                database_created = True

                yield

            finally:
                db.session.remove()

                if database_created:
                    db.drop_all()

                test_engine.dispose()
                engines[None] = original_engine

    finally:
        flask_app.config[
            "SQLALCHEMY_DATABASE_URI"
        ] = original_database_uri


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from app import limiter
    limiter.storage.reset()

@pytest.fixture
def client(test_database):
    with flask_app.test_client() as test_client:
        yield test_client

def test_csv_export_requires_login(client):
    response = client.get(
        "/applications/export",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_delete_application_requires_login(client):
    response = client.post(
        "/applications/1/delete",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_edit_application_requires_login(client):
    response = client.get(
        "/applications/1/edit",
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

def test_logout_rejects_get_request(client):
    from models.user import User
    from extensions import db
    from werkzeug.security import generate_password_hash

    user = User(
        name="Logout Method Test",
        email="logoutmethod@example.com",
        password_hash=generate_password_hash("Password123!"),
    )
    db.session.add(user)
    db.session.commit()

    # Log in first.
    client.post(
        "/login",
        data={
            "email": "logoutmethod@example.com",
            "password": "Password123!",
        },
    )

    # Attempt logout using GET instead of POST.
    response = client.get(
        "/logout",
        follow_redirects=False,
    )

    assert response.status_code == 405

    # Confirm the user is still logged in.
    dashboard = client.get("/applications")
    assert dashboard.status_code == 200

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

    # Log in with the correct password.
    client.post(
        "/login",
        data={
            "email": "passwordtest@example.com",
            "password": "CorrectPass123!",
        },
    )

    # Submit a password change with the wrong current password.
    response = client.post(
        "/change-password",
        data={
            "current_password": "WrongPass123!",
            "new_password": "NewSecurePass456!",
            "confirm_password": "NewSecurePass456!",
        },
        follow_redirects=True,
    )

    db.session.refresh(user)

    assert not check_password_hash(
        user.password_hash,
        "NewSecurePass456!",
    )
