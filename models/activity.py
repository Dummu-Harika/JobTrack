
from extensions import db


class Activity(db.Model):
    __tablename__ = "activities"

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

    application_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "applications.id",
            ondelete="SET NULL",
            name="fk_activities_application_id",
        ),
        nullable=True,
    )

    action = db.Column(
        db.String(50),
        nullable=False,
    )

    description = db.Column(
        db.String(500),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )
