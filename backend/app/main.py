import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db

from app.models.profile import Profile
from app.models.application import Application

from app.schemas.profile import ProfileCreate

from app.browser.browser import Browser
from app.agents.form_agent import analyze_form


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AI Internship Application Agent"
)


@app.get("/")
async def root():

    return {
        "message": "AI Internship Agent running"
    }


@app.post("/profile")
async def create_profile(
    profile: ProfileCreate,
    db: Session = Depends(get_db)
):

    new_profile = Profile(
        name=profile.name,
        email=profile.email,
        phone=profile.phone,
        location=profile.location,
        degree=profile.degree,
        university=profile.university,
        graduation_year=profile.graduation_year,
        skills=profile.skills,
        projects=profile.projects,
        experience=profile.experience,
        github=profile.github,
        linkedin=profile.linkedin,
        portfolio=profile.portfolio
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return {
        "profile_id": new_profile.id,
        "message": "Profile created"
    }


@app.post("/agent/apply")
async def apply_to_job(
    url: str,
    profile_id: int,
    db: Session = Depends(get_db)
):

    profile = db.query(Profile).filter(
        Profile.id == profile_id
    ).first()

    if not profile:

        return {
            "error": "Profile not found"
        }

    profile_data = {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "degree": profile.degree,
        "university": profile.university,
        "graduation_year": profile.graduation_year,
        "skills": profile.skills,
        "projects": profile.projects,
        "experience": profile.experience,
        "github": profile.github,
        "linkedin": profile.linkedin,
        "portfolio": profile.portfolio
    }

    browser = Browser()

    try:

        await browser.start()

        await browser.open(url)

        page_content = await browser.get_page_content()

        fields = await analyze_form(
            page_content,
            profile_data
        )

        application = Application(
            profile_id=profile_id,
            job_url=url,
            application_url=url,
            status="form_analyzed"
        )

        db.add(application)
        db.commit()

        return {
            "status": "form_analyzed",
            "fields": fields
        }

    except Exception as e:

        return {
            "status": "failed",
            "error": str(e)
        }