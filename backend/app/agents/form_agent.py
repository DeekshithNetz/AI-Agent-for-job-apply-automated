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

        try:

            # =========================================
            # RESUME / FILE
            # =========================================

            # =========================================
            # RESUME / FILE UPLOAD
            # =========================================

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

                    print("Detected file inputs:", count)
                    print("Resume path:", resume_path)

                    if count == 0:
                        results.append({
                            "field": description,
                            "status": "upload_field_not_found"
                        })
                        continue

                    uploaded = False

                    for i in range(count):

                        file_input = file_inputs.nth(i)

                        try:

                            await file_input.set_input_files(
                                resume_path
                            )

                            print(
                                f"Resume uploaded using file input {i}"
                            )

                            uploaded = True
                            break

                        except Exception as e:

                            print(
                                f"File input {i} failed:",
                                str(e)
                            )

                    results.append({
                        "field": description,
                        "status": (
                            "uploaded"
                            if uploaded
                            else "upload_failed"
                        )
                    })

                except Exception as e:

                    results.append({
                        "field": description,
                        "status": "upload_failed",
                        "error": str(e)
                    })

                continue

            # =========================================
            # CHECKBOX
            # =========================================

            if field_type == "checkbox":

                locator = page.get_by_label(
                    description,
                    exact=False
                ).first

                if await locator.count() > 0:

                    if not await locator.is_checked():
                        await locator.check()

                    results.append({
                        "field": description,
                        "status": "checked"
                    })

                else:

                    # fallback
                    checkboxes = page.locator(
                        'input[type="checkbox"]'
                    )

                    if await checkboxes.count() > 0:

                        await checkboxes.first.check()

                        results.append({
                            "field": description,
                            "status": "checked"
                        })

                    else:

                        results.append({
                            "field": description,
                            "status": "checkbox_not_found"
                        })

                continue

            # =========================================
            # SELECT / DROPDOWN
            # =========================================

            if field_type in [
                "select",
                "dropdown"
            ]:

                if value is None:
                    results.append({
                        "field": description,
                        "status": "no_value"
                    })
                    continue

                selects = page.locator("select")

                count = await selects.count()

                found = False

                for i in range(count):

                    select = selects.nth(i)

                    attrs = await select.evaluate("""
                        el => ({
                            name: el.name || "",
                            id: el.id || "",
                            aria: el.getAttribute("aria-label") || ""
                        })
                    """)

                    text = " ".join(
                        str(v).lower()
                        for v in attrs.values()
                    )

                    if any(
                        word.lower() in text
                        for word in description.split()
                        if len(word) > 3
                    ):

                        options = await select.locator(
                            "option"
                        ).all_text_contents()

                        matching = None

                        for option in options:

                            if str(value).lower() in option.lower():
                                matching = option
                                break

                        if matching:

                            await select.select_option(
                                label=matching
                            )

                            found = True

                            break

                results.append({
                    "field": description,
                    "status": (
                        "selected"
                        if found
                        else "dropdown_not_found"
                    )
                })

                continue

            # =========================================
            # RADIO BUTTON
            # =========================================

            if field_type == "radio":

                if value is None:
                    continue

                try:

                    radio = page.get_by_label(
                        str(value),
                        exact=False
                    ).first

                    if await radio.count() > 0:

                        await radio.check()

                        results.append({
                            "field": description,
                            "status": "selected"
                        })

                    else:

                        results.append({
                            "field": description,
                            "status": "radio_not_found"
                        })

                except Exception as e:

                    results.append({
                        "field": description,
                        "status": "radio_failed",
                        "error": str(e)
                    })

                continue

            # =========================================
            # TEXT / TEXTAREA
            # =========================================

            if field_type in [
                "text",
                "textarea",
                "email",
                "tel",
                "number"
            ]:

                if value is None:
                    continue

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

                # fallback
                elements = page.locator(
                    "input, textarea"
                )

                count = await elements.count()

                found = False

                keywords = [
                    word.lower()
                    for word in description.split()
                    if len(word) > 3
                ]

                for i in range(count):

                    element = elements.nth(i)

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
                        keyword in text
                        for keyword in keywords
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

                continue

            # =========================================
            # UNKNOWN FIELD
            # =========================================

            results.append({
                "field": description,
                "status": "unsupported_field_type",
                "type": field_type
            })

        except Exception as e:

            results.append({
                "field": description,
                "status": "failed",
                "error": str(e)
            })

    return results