# app/agents/application_agent.py

import asyncio

from app.agents.navigation_agent import (
    find_next_button,
    click_navigation
)


# ============================================================
# APPLICATION AGENT
# ============================================================

async def run_application(
    page,
    analyze_page,
    execute_form,
    resume_path=None,
    max_steps=10
):

    all_results = []

    # ========================================================
    # APPLICATION LOOP
    # ========================================================

    for step in range(max_steps):

        step_number = step + 1

        print(
            f"\n========== APPLICATION STEP "
            f"{step_number} =========="
        )

        # ====================================================
        # ANALYZE CURRENT PAGE
        # ====================================================

        try:

            fields = await analyze_page()

        except Exception as e:

            print(
                "Page analysis failed:",
                str(e)
            )

            return {
                "status":
                    "analysis_failed",

                "step":
                    step_number,

                "error":
                    str(e),

                "fields":
                    all_results
            }

        # ----------------------------------------------------
        # Validate AI response
        # ----------------------------------------------------

        if fields is None:

            fields = []

        if not isinstance(
            fields,
            list
        ):

            print(
                "AI returned invalid field structure"
            )

            return {
                "status":
                    "invalid_ai_response",

                "step":
                    step_number,

                "fields":
                    all_results
            }

        print(
            f"AI detected {len(fields)} fields"
        )

        # ====================================================
        # EXECUTE FORM
        # ====================================================

        try:

            results = await execute_form(
                page,
                fields,
                resume_path
            )

        except Exception as e:

            print(
                "Form execution failed:",
                str(e)
            )

            return {
                "status":
                    "form_execution_failed",

                "step":
                    step_number,

                "error":
                    str(e),

                "fields":
                    all_results
            }

        if results:

            all_results.extend(
                results
            )

        # ====================================================
        # HTML VALIDATION
        # ====================================================

        try:

            invalid_elements = (
                await page.locator(
                    ":invalid"
                ).evaluate_all(
                    """
                    elements => elements.map(
                        el => ({
                            tag:
                                el.tagName,

                            type:
                                el.type || "",

                            name:
                                el.name || "",

                            id:
                                el.id || "",

                            value:
                                el.value || "",

                            required:
                                !!el.required,

                            ariaLabel:
                                el.getAttribute(
                                    "aria-label"
                                ) || "",

                            placeholder:
                                el.getAttribute(
                                    "placeholder"
                                ) || ""
                        })
                    )
                    """
                )
            )

        except Exception as e:

            print(
                "Validation inspection failed:",
                str(e)
            )

            invalid_elements = []

        print(
            "INVALID ELEMENTS:"
        )

        print(
            invalid_elements
        )

        # ====================================================
        # FILTER VISIBLE INVALID ELEMENTS
        # ====================================================

        visible_invalid = []

        for invalid in invalid_elements:

            try:

                element_id = (
                    invalid.get(
                        "id"
                    )
                )

                element = None

                # ------------------------------------------------
                # ID lookup
                # ------------------------------------------------

                if element_id:

                    try:

                        element = page.locator(
                            f"#{element_id}"
                        ).first

                        if (
                            await element.count()
                            == 0
                        ):

                            element = None

                    except Exception:

                        element = None

                # ------------------------------------------------
                # If ID isn't available, use attributes.
                # ------------------------------------------------

                if element is None:

                    name = invalid.get(
                        "name",
                        ""
                    )

                    if name:

                        try:

                            element = page.locator(
                                "[name]"
                            ).filter(
                                has=page.locator(
                                    f'[name="{name}"]'
                                )
                            ).first

                        except Exception:

                            element = None

                # ------------------------------------------------
                # Only visible invalid fields matter.
                # ------------------------------------------------

                if element is not None:

                    try:

                        if await element.is_visible():

                            visible_invalid.append(
                                invalid
                            )

                    except Exception:

                        pass

            except Exception:

                continue

        if visible_invalid:

            print(
                "VISIBLE INVALID ELEMENTS:"
            )

            print(
                visible_invalid
            )

            return {
                "status":
                    "validation_failed",

                "invalid_fields":
                    len(visible_invalid),

                "invalid_elements":
                    visible_invalid,

                "step":
                    step_number,

                "fields":
                    all_results
            }

        # ====================================================
        # FIND NAVIGATION
        #
        # IMPORTANT:
        #
        # find_next_button() returns:
        #
        #     button, action
        #
        # NOT:
        #
        #     frame, button, action
        # ====================================================

        try:

            button, action = (
                await find_next_button(
                    page
                )
            )

        except Exception as e:

            print(
                "Navigation detection failed:",
                str(e)
            )

            return {
                "status":
                    "navigation_detection_failed",

                "step":
                    step_number,

                "error":
                    str(e),

                "fields":
                    all_results
            }

        print(
            f"Navigation: {action}"
        )

        # ====================================================
        # NO NAVIGATION
        # ====================================================

        if button is None:

            # ------------------------------------------------
            # One additional detection attempt.
            #
            # This is useful for forms whose DOM is still
            # settling after field filling.
            # ------------------------------------------------

            print(
                "Navigation not found. "
                "Waiting for DOM update..."
            )

            await page.wait_for_timeout(
                1000
            )

            try:

                button, action = (
                    await find_next_button(
                        page
                    )
                )

            except Exception as e:

                print(
                    "Navigation retry failed:",
                    str(e)
                )

                button = None
                action = None

            if button is None:

                return {
                    "status":
                        "no_navigation_button",

                    "step":
                        step_number,

                    "fields":
                        all_results
                }

        # ====================================================
        # NEXT
        # ====================================================

        if action == "next":

            print(
                "\nMoving to next "
                "application page..."
            )

            try:

                clicked = await click_navigation(
                    page,
                    button,
                    "next"
                )

            except Exception as e:

                print(
                    "Next navigation failed:",
                    str(e)
                )

                clicked = False

            if not clicked:

                return {
                    "status":
                        "next_click_failed",

                    "step":
                        step_number,

                    "fields":
                        all_results
                }

            # ------------------------------------------------
            # Give the form time to render its next section.
            # ------------------------------------------------

            await page.wait_for_timeout(
                1500
            )

            continue

        # ====================================================
        # SUBMIT
        # ====================================================

        if action == "submit":

            print(
                "\nSubmitting application..."
            )

            try:

                clicked = await click_navigation(
                    page,
                    button,
                    "submit"
                )

            except Exception as e:

                print(
                    "Submit navigation failed:",
                    str(e)
                )

                clicked = False

            if not clicked:

                return {
                    "status":
                        "submit_click_failed",

                    "step":
                        step_number,

                    "fields":
                        all_results
                }

            # ------------------------------------------------
            # Wait for submission response.
            # ------------------------------------------------

            await page.wait_for_timeout(
                2000
            )

            try:

                body_text = (
                    await page.locator(
                        "body"
                    ).inner_text()
                ).lower()

            except Exception:

                body_text = ""

            # ------------------------------------------------
            # Common successful submission indicators
            # ------------------------------------------------

            success_indicators = [

                "your response has been recorded",

                "response has been recorded",

                "thank you for submitting",

                "thank you for your response",

                "application submitted",

                "successfully submitted",

                "submission received",

            ]

            success = any(
                indicator in body_text
                for indicator
                in success_indicators
            )

            if success:

                print(
                    "Application submission confirmed."
                )

                return {
                    "status":
                        "submitted",

                    "message":
                        "Application submitted successfully",

                    "steps":
                        step_number,

                    "fields":
                        all_results
                }

            # ------------------------------------------------
            # No standard success text.
            #
            # The click was successfully executed, so report
            # that the submit action was executed rather than
            # falsely reporting a click failure.
            # ------------------------------------------------

            print(
                "Submit action executed. "
                "No standard success message detected."
            )

            return {
                "status":
                    "submitted",

                "message":
                    "Submit action executed",

                "steps":
                    step_number,

                "fields":
                    all_results
            }

        # ====================================================
        # UNKNOWN ACTION
        # ====================================================

        return {
            "status":
                "unknown_navigation_action",

            "action":
                action,

            "step":
                step_number,

            "fields":
                all_results
        }

    # ========================================================
    # MAX STEPS
    # ========================================================

    return {
        "status":
            "max_steps_reached",

        "steps":
            max_steps,

        "fields":
            all_results
    }