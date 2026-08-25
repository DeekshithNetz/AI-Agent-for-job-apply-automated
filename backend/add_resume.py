from pathlib import Path

from app.database import SessionLocal
from app.models.profile import Profile


resume_path = Path(__file__).resolve().parent / "uploads" / "sample.pdf"

db = SessionLocal()

try:

    profile = db.query(Profile).filter(
        Profile.id == 2
    ).first()

    if not profile:
        print("Profile ID 2 not found.")
        exit()

    if not resume_path.exists():
        print(f"Resume not found: {resume_path}")
        exit()

    profile.resume_path = str(resume_path)

    db.commit()

    print("Resume added successfully!")
    print("Profile ID:", profile.id)
    print("Resume:", profile.resume_path)

finally:

    db.close()