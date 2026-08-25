import json

from app.ai.gemini import ask_ai


async def analyze_form(page_content: str, profile: dict):

    prompt = f"""
You are an AI job application form analysis agent.

Candidate profile:

{json.dumps(profile, indent=2)}

Application page:

{page_content}

Identify the fields that should be completed.

Return ONLY valid JSON.

Format:

[
    {{
        "field_description": "Full Name",
        "field_type": "text",
        "value": "Deekshith",
        "source": "profile",
        "confidence": 0.99
    }}
]

Allowed field_type:

text
textarea
select
checkbox
radio
file

Rules:

1. Use candidate information when available.
2. Never invent qualifications.
3. Never invent experience.
4. Never invent education.
5. For questions requiring personalized answers,
   generate an answer using only the candidate's
   real profile, projects and experience.
6. Resume/CV upload should have value null.
7. Consent checkboxes can have value true.
8. Return JSON only.
"""

    result = await ask_ai(prompt)

    result = result.strip()

    if result.startswith("```"):
        result = result.replace("```json", "")
        result = result.replace("```", "")

    return json.loads(result)
async def execute_form(page, fields, resume_path=None):

    results = []

    for field in fields:

        description = field.get("field_description", "")
        field_type = field.get("field_type", "")
        value = field.get("value")
        confidence = field.get("confidence", 0)

        if confidence < 0.70:
            results.append({
                "field": description,
                "status": "skipped_low_confidence"
            })
            continue

        # -------------------------
        # FILE / RESUME
        # -------------------------
        if field_type == "file":

            if not resume_path:
                results.append({
                    "field": description,
                    "status": "resume_not_available"
                })
                continue

            try:

                file_inputs = page.locator(
                    'input[type="file"]'
                )

                count = await file_inputs.count()

                uploaded = False

                for i in range(count):

                    element = file_inputs.nth(i)

                    attrs = await element.evaluate("""
                        el => ({
                            name: el.name || "",
                            id: el.id || "",
                            accept: el.accept || "",
                            aria: el.getAttribute("aria-label") || ""
                        })
                    """)

                    text = " ".join(
                        str(v).lower()
                        for v in attrs.values()
                    )

                    if (
                        "resume" in text
                        or "cv" in text
                        or "curriculum" in text
                        or "pdf" in text
                    ):

                        await element.set_input_files(
                            resume_path
                        )

                        uploaded = True
                        break

                results.append({
                    "field": description,
                    "status": (
                        "uploaded"
                        if uploaded
                        else "upload_field_not_found"
                    )
                })

            except Exception as e:

                results.append({
                    "field": description,
                    "status": "upload_failed",
                    "error": str(e)
                })

            continue

        # -------------------------
        # CHECKBOX
        # -------------------------
        if field_type == "checkbox":

            try:

                checkbox = page.get_by_label(
                    description,
                    exact=False
                ).first

                if await checkbox.count() > 0:

                    if not await checkbox.is_checked():
                        await checkbox.check()

                    results.append({
                        "field": description,
                        "status": "checked"
                    })

                else:

                    results.append({
                        "field": description,
                        "status": "checkbox_not_found"
                    })

            except Exception as e:

                results.append({
                    "field": description,
                    "status": "checkbox_failed",
                    "error": str(e)
                })

            continue

        # -------------------------
        # TEXT / TEXTAREA
        # -------------------------
        if field_type in ["text", "textarea"]:

            if value is None:
                continue

            try:

                # First try label
                locator = page.get_by_label(
                    description,
                    exact=False
                ).first

                if await locator.count() > 0:

                    await locator.fill(
                        str(value)
                    )

                    results.append({
                        "field": description,
                        "status": "filled"
                    })

                    continue

                # Fallback: inspect inputs
                locator = page.locator(
                    "input, textarea"
                )

                count = await locator.count()

                found = False

                words = [
                    word.lower()
                    for word in description.split()
                    if len(word) > 3
                ]

                for i in range(count):

                    element = locator.nth(i)

                    attrs = await element.evaluate("""
                        el => ({
                            name: el.name || "",
                            id: el.id || "",
                            placeholder: el.placeholder || "",
                            aria: el.getAttribute("aria-label") || ""
                        })
                    """)

                    text = " ".join(
                        str(v).lower()
                        for v in attrs.values()
                    )

                    if any(
                        word in text
                        for word in words
                    ):

                        await element.fill(
                            str(value)
                        )

                        found = True
                        break

                results.append({
                    "field": description,
                    "status": (
                        "filled"
                        if found
                        else "field_not_found"
                    )
                })

            except Exception as e:

                results.append({
                    "field": description,
                    "status": "fill_failed",
                    "error": str(e)
                })

    return results