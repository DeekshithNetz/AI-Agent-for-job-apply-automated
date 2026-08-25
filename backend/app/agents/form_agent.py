import json

from app.ai.gemini import ask_ai


# =========================================================
# ANALYZE FORM
# =========================================================

async def analyze_form(page_content: str, profile: dict):

    prompt = f"""
You are an AI job application form analysis agent.

Candidate profile:

{json.dumps(profile, indent=2)}

Application page:

{page_content}

Identify ONLY the fields that should be completed.

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
email
tel
number
select
radio
checkbox
file
multi_select
skills

Rules:

1. Use candidate information when available.
2. Never invent qualifications.
3. Never invent experience.
4. Never invent education.
5. Never invent skills.
6. Never invent projects.
7. Never invent personal information.
8. Resume/CV upload must have value null.
9. Consent checkbox can have value true.
10. For skills:
    - If the form is a normal text field, use field_type "skills".
    - If it is a <select multiple>, use field_type "multi_select".
11. For gender and similar options use field_type "radio".
12. For normal dropdowns use field_type "select".
13. For personalized questions, generate an answer only from
    the candidate's real profile, projects and experience.
14. confidence must be between 0 and 1.
15. Return JSON only.
"""

    result = await ask_ai(prompt)

    result = result.strip()

    if result.startswith("```"):

        result = result.replace(
            "```json",
            ""
        )

        result = result.replace(
            "```",
            ""
        )

    return json.loads(result)


# =========================================================
# HELPER
# =========================================================

async def get_element_info(element):

    return await element.evaluate("""
        el => ({
            tag: el.tagName.toLowerCase(),
            type: (el.type || "").toLowerCase(),
            name: el.name || "",
            id: el.id || "",
            placeholder: el.placeholder || "",
            aria: el.getAttribute("aria-label") || "",
            title: el.getAttribute("title") || "",
            required: !!el.required,
            multiple: !!el.multiple
        })
    """)


def build_search_text(attrs):

    return " ".join([
        attrs.get("name", ""),
        attrs.get("id", ""),
        attrs.get("placeholder", ""),
        attrs.get("aria", ""),
        attrs.get("title", "")
    ]).lower()


def get_keywords(description):

    return [
        word.lower()
        for word in description.split()
        if len(word) > 2
    ]


def matches_description(description, attrs):

    searchable = build_search_text(attrs)

    keywords = get_keywords(description)

    if not keywords:
        return False

    return any(
        keyword in searchable
        for keyword in keywords
    )


# =========================================================
# FILE UPLOAD
# =========================================================

async def handle_file(
    page,
    description,
    resume_path
):

    if not resume_path:

        return {
            "field": description,
            "status": "resume_not_available"
        }

    file_inputs = page.locator(
        'input[type="file"]'
    )

    count = await file_inputs.count()

    print(
        "Detected file inputs:",
        count
    )

    if count == 0:

        return {
            "field": description,
            "status": "upload_field_not_found"
        }

    for i in range(count):

        try:

            file_input = file_inputs.nth(i)

            await file_input.set_input_files(
                resume_path
            )

            print(
                f"Resume uploaded using file input {i}"
            )

            return {
                "field": description,
                "status": "uploaded"
            }

        except Exception as e:

            print(
                f"File input {i} failed:",
                str(e)
            )

    return {
        "field": description,
        "status": "upload_failed"
    }


# =========================================================
# CHECKBOX
# =========================================================

async def handle_checkbox(
    page,
    description,
    value
):

    try:

        locator = page.get_by_label(
            description,
            exact=False
        ).first

        if await locator.count() > 0:

            if not await locator.is_checked():

                await locator.check()

            return {
                "field": description,
                "status": "checked"
            }

    except Exception:
        pass

    checkboxes = page.locator(
        'input[type="checkbox"]'
    )

    count = await checkboxes.count()

    for i in range(count):

        checkbox = checkboxes.nth(i)

        try:

            if not await checkbox.is_visible():
                continue

            attrs = await get_element_info(
                checkbox
            )

            if matches_description(
                description,
                attrs
            ):

                if not await checkbox.is_checked():

                    await checkbox.check()

                return {
                    "field": description,
                    "status": "checked"
                }

        except Exception:
            continue

    return {
        "field": description,
        "status": "checkbox_not_found"
    }


# =========================================================
# RADIO
# =========================================================

async def handle_radio(
    page,
    description,
    value
):

    if value is None:

        return {
            "field": description,
            "status": "no_value"
        }

    requested = str(value).strip().lower()

    # -----------------------------------------------------
    # First try label
    # -----------------------------------------------------

    try:

        locator = page.get_by_label(
            str(value),
            exact=False
        ).first

        if await locator.count() > 0:

            await locator.check()

            return {
                "field": description,
                "status": "selected"
            }

    except Exception:
        pass

    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    radios = page.locator(
        'input[type="radio"]'
    )

    count = await radios.count()

    for i in range(count):

        radio = radios.nth(i)

        try:

            attrs = await get_element_info(
                radio
            )

            radio_value = (
                attrs.get("type", "")
            )

            raw_value = await radio.get_attribute(
                "value"
            ) or ""

            radio_id = await radio.get_attribute(
                "id"
            ) or ""

            label_text = ""

            if radio_id:

                try:

                    label = page.locator(
                        f'label[for="{radio_id}"]'
                    )

                    if await label.count() > 0:

                        label_text = (
                            await label.inner_text()
                            or ""
                        )

                except Exception:
                    pass

            candidates = [
                raw_value,
                label_text
            ]

            for candidate in candidates:

                candidate = str(
                    candidate
                ).strip().lower()

                if (
                    candidate == requested
                    or requested in candidate
                    or candidate in requested
                ):

                    await radio.check()

                    return {
                        "field": description,
                        "status": "selected"
                    }

        except Exception:
            continue

    return {
        "field": description,
        "status": "radio_not_found"
    }


# =========================================================
# SELECT
# =========================================================

async def handle_select(
    page,
    description,
    value
):

    if value is None:

        return {
            "field": description,
            "status": "no_value"
        }

    selects = page.locator(
        "select"
    )

    count = await selects.count()

    for i in range(count):

        select = selects.nth(i)

        try:

            if not await select.is_visible():
                continue

            attrs = await get_element_info(
                select
            )

            if not matches_description(
                description,
                attrs
            ):
                continue

            # ------------------------------------------------
            # Multiple select
            # ------------------------------------------------

            if attrs["multiple"]:

                values = (
                    value
                    if isinstance(value, list)
                    else [value]
                )

                selected_values = []

                options = select.locator(
                    "option"
                )

                option_count = await options.count()

                for j in range(option_count):

                    option = options.nth(j)

                    option_text = (
                        await option.text_content()
                        or ""
                    ).strip()

                    option_value = (
                        await option.get_attribute(
                            "value"
                        )
                        or ""
                    )

                    for requested in values:

                        if (
                            str(requested).lower()
                            in option_text.lower()
                        ):

                            if option_value:

                                selected_values.append(
                                    option_value
                                )

                            break

                if selected_values:

                    await select.select_option(
                        selected_values
                    )

                    return {
                        "field": description,
                        "status": "selected",
                        "values": values
                    }

                return {
                    "field": description,
                    "status": "option_not_found"
                }

            # ------------------------------------------------
            # Normal select
            # ------------------------------------------------

            requested = str(
                value
            ).strip().lower()

            options = select.locator(
                "option"
            )

            option_count = await options.count()

            for j in range(option_count):

                option = options.nth(j)

                option_text = (
                    await option.text_content()
                    or ""
                ).strip()

                option_value = (
                    await option.get_attribute(
                        "value"
                    )
                    or ""
                )

                if (
                    requested == option_text.lower()
                    or requested in option_text.lower()
                    or option_text.lower() in requested
                ):

                    if option_value:

                        await select.select_option(
                            option_value
                        )

                    else:

                        await select.select_option(
                            label=option_text
                        )

                    return {
                        "field": description,
                        "status": "selected"
                    }

        except Exception as e:

            print(
                "Select error:",
                str(e)
            )

    return {
        "field": description,
        "status": "select_not_found"
    }


# =========================================================
# SKILLS
# Handles:
#
# 1. <input>
# 2. <textarea>
# 3. <select multiple>
# =========================================================

async def handle_skills(
    page,
    description,
    value
):

    if value is None:

        return {
            "field": description,
            "status": "no_value"
        }

    values = (
        value
        if isinstance(value, list)
        else [
            x.strip()
            for x in str(value).split(",")
            if x.strip()
        ]
    )

    elements = page.locator(
        "input, textarea, select"
    )

    count = await elements.count()

    skill_keywords = [
        "skill",
        "skills",
        "technology",
        "technologies",
        "technical",
        "expertise",
        "tech stack"
    ]

    for i in range(count):

        element = elements.nth(i)

        try:

            if not await element.is_visible():
                continue

            attrs = await get_element_info(
                element
            )

            searchable = build_search_text(
                attrs
            )

            if not any(
                keyword in searchable
                for keyword in skill_keywords
            ):
                continue

            tag = attrs["tag"]
            input_type = attrs["type"]

            # ------------------------------------------------
            # SELECT MULTIPLE
            # ------------------------------------------------

            if (
                tag == "select"
                and attrs["multiple"]
            ):

                options = element.locator(
                    "option"
                )

                option_count = await options.count()

                selected_values = []

                for j in range(option_count):

                    option = options.nth(j)

                    option_text = (
                        await option.text_content()
                        or ""
                    ).strip()

                    option_value = (
                        await option.get_attribute(
                            "value"
                        )
                        or ""
                    )

                    for requested in values:

                        if (
                            str(requested).lower()
                            in option_text.lower()
                        ):

                            if option_value:

                                selected_values.append(
                                    option_value
                                )

                            break

                if selected_values:

                    await element.select_option(
                        selected_values
                    )

                    return {
                        "field": description,
                        "status": "selected",
                        "values": values
                    }

                return {
                    "field": description,
                    "status": "skill_options_not_found"
                }

            # ------------------------------------------------
            # NORMAL INPUT
            # ------------------------------------------------

            if (
                tag == "input"
                and input_type in [
                    "",
                    "text"
                ]
            ):

                skills_text = ", ".join(
                    str(v)
                    for v in values
                )

                await element.fill(
                    skills_text
                )

                return {
                    "field": description,
                    "status": "filled",
                    "value": skills_text
                }

            # ------------------------------------------------
            # TEXTAREA
            # ------------------------------------------------

            if tag == "textarea":

                skills_text = ", ".join(
                    str(v)
                    for v in values
                )

                await element.fill(
                    skills_text
                )

                return {
                    "field": description,
                    "status": "filled",
                    "value": skills_text
                }

        except Exception:
            continue

    return {
        "field": description,
        "status": "skills_field_not_found"
    }


# =========================================================
# TEXT FIELDS
# =========================================================

async def handle_text(
    page,
    description,
    value
):

    if value is None:

        return {
            "field": description,
            "status": "no_value"
        }

    # -----------------------------------------------------
    # Try accessible label first
    # -----------------------------------------------------

    try:

        locator = page.get_by_label(
            description,
            exact=False
        ).first

        if await locator.count() > 0:

            await locator.fill(
                str(value)
            )

            return {
                "field": description,
                "status": "filled"
            }

    except Exception:
        pass

    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    elements = page.locator(
        "input, textarea"
    )

    count = await elements.count()

    for i in range(count):

        element = elements.nth(i)

        try:

            if not await element.is_visible():
                continue

            attrs = await get_element_info(
                element
            )

            if matches_description(
                description,
                attrs
            ):

                if attrs["type"] in [
                    "radio",
                    "checkbox",
                    "file",
                    "hidden"
                ]:

                    continue

                await element.fill(
                    str(value)
                )

                return {
                    "field": description,
                    "status": "filled"
                }

        except Exception:
            continue

    return {
        "field": description,
        "status": "field_not_found"
    }


# =========================================================
# MAIN EXECUTOR
# =========================================================

async def execute_form(
    page,
    fields,
    resume_path=None
):

    results = []

    for field in fields:

        description = field.get(
            "field_description",
            ""
        )

        field_type = field.get(
            "field_type",
            ""
        ).lower().strip()

        value = field.get(
            "value"
        )

        confidence = field.get(
            "confidence",
            0
        )

        print(
            f"Processing: {description} | "
            f"type={field_type} | "
            f"value={value} | "
            f"confidence={confidence}"
        )

        # -------------------------------------------------
        # Confidence
        # -------------------------------------------------

        if confidence < 0.70:

            results.append({
                "field": description,
                "status":
                    "skipped_low_confidence"
            })

            continue

        try:

            # =============================================
            # FILE
            # =============================================

            if field_type == "file":

                result = await handle_file(
                    page,
                    description,
                    resume_path
                )

                results.append(result)

                continue

            # =============================================
            # CHECKBOX
            # =============================================

            if field_type == "checkbox":

                result = await handle_checkbox(
                    page,
                    description,
                    value
                )

                results.append(result)

                continue

            # =============================================
            # RADIO
            # =============================================

            if field_type == "radio":

                result = await handle_radio(
                    page,
                    description,
                    value
                )

                results.append(result)

                continue

            # =============================================
            # SELECT
            # =============================================

            if field_type in [
                "select",
                "dropdown"
            ]:

                result = await handle_select(
                    page,
                    description,
                    value
                )

                results.append(result)

                continue

            # =============================================
            # MULTI SELECT
            # =============================================

            if field_type in [
                "multi_select",
                "multiselect"
            ]:

                result = await handle_select(
                    page,
                    description,
                    value
                )

                results.append(result)

                continue

            # =============================================
            # SKILLS
            # =============================================

            if field_type in [
                "skills",
                "skill",
                "tags",
                "multi_value"
            ]:

                result = await handle_skills(
                    page,
                    description,
                    value
                )

                results.append(result)

                continue

            # =============================================
            # TEXT
            # =============================================

            if field_type in [
                "text",
                "textarea",
                "email",
                "tel",
                "number"
            ]:

                result = await handle_text(
                    page,
                    description,
                    value
                )

                results.append(result)

                continue

            # =============================================
            # UNKNOWN
            # =============================================

            results.append({
                "field": description,
                "status":
                    "unsupported_field_type",
                "type":
                    field_type
            })

        except Exception as e:

            results.append({
                "field": description,
                "status": "failed",
                "error": str(e)
            })

    return results