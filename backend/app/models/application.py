from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class Application(Base):

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)

    profile_id = Column(Integer)

    job_url = Column(String(1000))

    application_url = Column(String(1000))

    company = Column(String(300))

    role = Column(String(300))

    status = Column(String(100), default="started")

    error = Column(Text, nullable=True)