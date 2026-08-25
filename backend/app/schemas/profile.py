from pydantic import BaseModel


class ProfileCreate(BaseModel):
    name: str
    email: str
    phone: str

    location: str

    degree: str
    university: str

    graduation_year: int

    skills: str
    projects: str
    experience: str

    github: str = ""
    linkedin: str = ""
    portfolio: str = ""