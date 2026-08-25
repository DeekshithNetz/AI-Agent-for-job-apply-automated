from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class Profile(Base):

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))

    location = Column(String(200))

    degree = Column(String(200))
    university = Column(String(300))

    graduation_year = Column(Integer)

    skills = Column(Text)
    projects = Column(Text)
    experience = Column(Text)

    github = Column(String(500))
    linkedin = Column(String(500))
    portfolio = Column(String(500))

    resume_path = Column(String(500))