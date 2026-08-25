import sys
import asyncio

if sys.platform == "win32":

    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )


from fastapi import (
    FastAPI,
    Depends
)

from sqlalchemy.orm import Session

from app.database import (
    Base,
    engine,
    get_db
)

from app.models.profile import Profile
from app.models.application import Application

from app.schemas.profile import ProfileCreate

from app.browser.browser import Browser

from app.agents.form_agent import (
    analyze_form,
    execute_form
)

from app.agents.application_agent import (
    run_application
)


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="AI Internship Application Agent"
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "message":
            "AI Internship Agent running"
    }


# =========================================================
# CREATE PROFILE
# =========================================================

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

    db.add(
        new_profile
    )

    db.commit()

    db.refresh(
        new_profile
    )

    return {

        "profile_id":
            new_profile.id,

        "message":
            "Profile created"
    }


# =========================================================
# APPLY TO JOB
# =========================================================

@app.post("/agent/apply")
async def apply_to_job(
    url: str,
    profile_id: int,
    db: Session = Depends(get_db)
):

    # =====================================================
    # GET PROFILE
    # =====================================================

    profile = db.query(
        Profile
    ).filter(
        Profile.id == profile_id
    ).first()

    if not profile:

        return {
            "status": "failed",
            "error": "Profile not found"
        }

    # =====================================================
    # PROFILE DATA FOR AI
    # =====================================================

    profile_data = {

        "name":
            profile.name,

        "email":
            profile.email,

        "phone":
            profile.phone,

        "location":
            profile.location,

        "degree":
            profile.degree,

        "university":
            profile.university,

        "graduation_year":
            profile.graduation_year,

        "skills":
            profile.skills,

        "projects":
            profile.projects,

        "experience":
            profile.experience,

        "github":
            profile.github,

        "linkedin":
            profile.linkedin,

        "portfolio":
            profile.portfolio
    }

    browser = Browser()

    try:

        # =================================================
        # START BROWSER
        # =================================================

        await browser.start()

        await browser.open(
            url
        )

        # =================================================
        # PAGE ANALYZER
        # =================================================

        async def analyze_current_page():

            page_content = (
                await browser.get_page_content()
            )

            return await analyze_form(
                page_content,
                profile_data
            )

        # =================================================
        # RUN APPLICATION AGENT
        # =================================================

        result = await run_application(

            page=browser.page,

            analyze_page=analyze_current_page,

            execute_form=execute_form,

            resume_path=profile.resume_path,

            max_steps=10
        )

        # =================================================
        # SAVE APPLICATION
        # =================================================

        if result.get("status") == "submitted":

            application = Application(

                profile_id=
                    profile_id,

                job_url=
                    url,

                application_url=
                    url,

                status=
                    "submitted"
            )

            db.add(
                application
            )

            db.commit()

        # =================================================
        # RETURN RESULT
        # =================================================

        return result

    except Exception as e:

        return {

            "status":
                "failed",

            "error":
                str(e)
        }

    finally:

        await browser.close()