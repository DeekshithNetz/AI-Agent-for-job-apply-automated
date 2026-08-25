async def find_next_button(page):

    buttons = page.locator(
        'button, '
        'input[type="button"], '
        'input[type="submit"], '
        'a[role="button"]'
    )

    count = await buttons.count()

    next_keywords = [
        "next",
        "continue",
        "proceed",
        "save & continue",
        "save and continue",
        "next step",
        "continue to next",
        "continue application",
        "go to next",
        "review"
    ]

    submit_keywords = [
        "submit",
        "submit application",
        "apply",
        "apply now",
        "finish",
        "finish application",
        "complete",
        "complete application",
        "send application"
    ]

    # =====================================================
    # LOOK FOR BUTTONS
    # =====================================================

    for i in range(count):

        element = buttons.nth(i)

        try:

            if not await element.is_visible():
                continue

            text = ""

            try:
                text = (
                    await element.inner_text()
                    or ""
                )
            except Exception:
                pass

            value = (
                await element.get_attribute(
                    "value"
                )
                or ""
            )

            aria = (
                await element.get_attribute(
                    "aria-label"
                )
                or ""
            )

            title = (
                await element.get_attribute(
                    "title"
                )
                or ""
            )

            combined = " ".join([
                text,
                value,
                aria,
                title
            ]).strip().lower()

            if not combined:
                continue

            print(
                f"Navigation candidate: {combined}"
            )

            # =================================================
            # SUBMIT
            # =================================================

            for keyword in submit_keywords:

                if keyword in combined:

                    print(
                        f"SUBMIT detected: {combined}"
                    )

                    return element, "submit"

            # =================================================
            # NEXT
            # =================================================

            for keyword in next_keywords:

                if keyword in combined:

                    print(
                        f"NEXT detected: {combined}"
                    )

                    return element, "next"

        except Exception as e:

            print(
                "Navigation detection error:",
                str(e)
            )

    return None, None