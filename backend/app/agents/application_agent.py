from app.agents.navigation_agent import (
    find_next_button
)


async def run_application(
    page,
    analyze_page,
    execute_form,
    resume_path=None,
    max_steps=10
):

    all_results = []

    for step in range(max_steps):

        print(
            f"\n========== APPLICATION STEP "
            f"{step + 1} =========="
        )

        # =====================================================
        # GET CURRENT PAGE
        # =====================================================

        fields = await analyze_page()

        print(
            f"AI detected {len(fields)} fields"
        )

        # =====================================================
        # EXECUTE CURRENT PAGE
        # =====================================================

        results = await execute_form(
            page,
            fields,
            resume_path
        )

        all_results.extend(
            results
        )

        # =====================================================
        # CHECK HTML VALIDATION
        # =====================================================

        invalid_elements = await page.locator(
            ":invalid"
        ).evaluate_all("""
            elements => elements.map(el => ({
                tag: el.tagName,
                type: el.type || "",
                name: el.name || "",
                id: el.id || "",
                value: el.value || "",
                required: el.required
            }))
        """)

        print(
            "INVALID ELEMENTS:"
        )

        print(
            invalid_elements
        )

        # =====================================================
        # VALIDATION FAILED
        # =====================================================

        if invalid_elements:

            return {
                "status":
                    "validation_failed",

                "invalid_fields":
                    len(invalid_elements),

                "invalid_elements":
                    invalid_elements,

                "step":
                    step + 1,

                "fields":
                    all_results
            }

        # =====================================================
        # FIND NAVIGATION
        # =====================================================

        button, action = await find_next_button(page)

        print(
            f"Navigation: {action}"
        )

        # =====================================================
        # NO BUTTON
        # =====================================================

        if button is None:

            return {
                "status":
                    "no_navigation_button",

                "step":
                    step + 1,

                "fields":
                    all_results
            }

        # =====================================================
        # SUBMIT
        # =====================================================

        if action == "submit":

            print(
                "Submitting application..."
            )

            await button.click()

            try:

                await page.wait_for_load_state(
                    "networkidle",
                    timeout=10000
                )

            except Exception:

                pass

            await page.wait_for_timeout(
                1500
            )

            return {
                "status":
                    "submitted",

                "message":
                    "Application submitted successfully",

                "steps":
                    step + 1,

                "fields":
                    all_results
            }

        # =====================================================
        # NEXT
        # =====================================================

        if action == "next":

            print(
                "Moving to next application page..."
            )

            await button.click()

            try:

                await page.wait_for_load_state(
                    "networkidle",
                    timeout=10000
                )

            except Exception:

                pass

            await page.wait_for_timeout(
                1000
            )

            continue

        # =====================================================
        # UNKNOWN ACTION
        # =====================================================

        return {
            "status":
                "unknown_navigation_action",

            "action":
                action,

            "step":
                step + 1,

            "fields":
                all_results
        }

    # =========================================================
    # MAX STEPS
    # =========================================================

    return {
        "status":
            "max_steps_reached",

        "steps":
            max_steps,

        "fields":
            all_results
    }