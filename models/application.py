
from extensions import db


VALID_STATUSES = (
    "Applied",
    "Assessment",
    "Interview",
    "Offer",
    "Rejected",
)


class Application(db.Model):
    __tablename__ = "applications"

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('Applied', 'Assessment', "
            "'Interview', 'Offer', 'Rejected')",
            name="check_application_status",
        ),
        db.Index(
            "ix_applications_user_status",
            "user_id",
            "status",
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    company_name = db.Column(
        db.String(150),
        nullable=False,
    )

    job_role = db.Column(
        db.String(150),
        nullable=False,
    )

    package_lpa = db.Column(
        db.Float,
        nullable=True,
    )

    location = db.Column(
        db.String(200),
        nullable=True,
    )

    application_date = db.Column(
        db.Date,
        nullable=True,
    )

    follow_up_date = db.Column(
        db.Date,
        nullable=True,
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="Applied",
    )

    job_url = db.Column(
        db.String(2048),
        nullable=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<Application {self.company_name} - "
            f"{self.job_role}>"
        )
