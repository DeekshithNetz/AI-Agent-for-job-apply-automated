# app/agents/navigation_agent.py

import asyncio
import re

#working
# ============================================================
# NAVIGATION KEYWORDS
# ============================================================

NEXT_EXACT = {
    "next",
    "continue",
    "proceed",
    "next step",
    "continue to next",
    "continue application",
    "continue to application",
    "go to next",
    "save and continue",
    "save & continue",
    "next page",
    "next section",
    "review",
}

SUBMIT_EXACT = {
    "submit",
    "submit application",
    "apply",
    "apply now",
    "finish",
    "finish application",
    "complete",
    "complete application",
    "send application",
    "send",
}


# ============================================================
# NORMALIZE
# ============================================================

def normalize_text(value):
    if not value:
        return ""

    value = str(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip().lower()


# ============================================================
# CLASSIFY
# ============================================================

def classify_navigation(text):

    text = normalize_text(text)

    if not text:
        return None

    if text in SUBMIT_EXACT:
        return "submit"

    if text in NEXT_EXACT:
        return "next"

    words = text.split()

    if len(words) <= 5:

        for keyword in SUBMIT_EXACT:
            if keyword in text:
                return "submit"

        for keyword in NEXT_EXACT:
            if keyword in text:
                return "next"

    return None


# ============================================================
# SAFE ATTRIBUTE
# ============================================================

async def get_attribute(element, name):

    try:
        value = await element.get_attribute(name)
        return value or ""
    except Exception:
        return ""


# ============================================================
# TAG NAME
# ============================================================

async def get_tag_name(element):

    try:
        return normalize_text(
            await element.evaluate(
                "el => el.tagName"
            )
        )
    except Exception:
        return ""


# ============================================================
# GET ELEMENT TEXT
# ============================================================

async def get_element_text(element):

    values = []

    try:
        text = await element.inner_text()

        if text:
            values.append(text)

    except Exception:
        pass

    try:
        text = await element.text_content()

        if text:
            values.append(text)

    except Exception:
        pass

    for attribute in [
        "aria-label",
        "title",
        "value",
        "data-label",
        "data-value",
        "name",
        "alt",
    ]:

        value = await get_attribute(
            element,
            attribute
        )

        if value:
            values.append(value)

    unique = []

    for value in values:

        normalized = normalize_text(value)

        if normalized and normalized not in unique:
            unique.append(normalized)

    return " ".join(unique)


# ============================================================
# ELEMENT DEBUG INFO
# ============================================================

async def debug_element(element, label="ELEMENT"):

    try:

        tag = await get_tag_name(element)

        role = await get_attribute(
            element,
            "role"
        )

        aria_label = await get_attribute(
            element,
            "aria-label"
        )

        jsname = await get_attribute(
            element,
            "jsname"
        )

        tabindex = await get_attribute(
            element,
            "tabindex"
        )

        aria_disabled = await get_attribute(
            element,
            "aria-disabled"
        )

        disabled = await get_attribute(
            element,
            "disabled"
        )

        text = await get_element_text(
            element
        )

        visible = await is_visible(
            element
        )

        try:
            box = await element.bounding_box()
        except Exception:
            box = None

        print(
            f"\n[NAV DEBUG] {label}"
        )

        print(
            f"[NAV DEBUG] tag           = {tag}"
        )

        print(
            f"[NAV DEBUG] role          = {role}"
        )

        print(
            f"[NAV DEBUG] text          = {text!r}"
        )

        print(
            f"[NAV DEBUG] aria-label    = {aria_label!r}"
        )

        print(
            f"[NAV DEBUG] jsname        = {jsname!r}"
        )

        print(
            f"[NAV DEBUG] tabindex      = {tabindex!r}"
        )

        print(
            f"[NAV DEBUG] disabled      = {disabled!r}"
        )

        print(
            f"[NAV DEBUG] aria-disabled = {aria_disabled!r}"
        )

        print(
            f"[NAV DEBUG] visible       = {visible}"
        )

        print(
            f"[NAV DEBUG] bounding_box  = {box}"
        )

    except Exception as e:

        print(
            f"[NAV DEBUG] Debug failed: {e}"
        )


# ============================================================
# VISIBILITY
# ============================================================

async def is_visible(element):

    try:
        return await element.is_visible()
    except Exception:
        return False


# ============================================================
# CLICKABLE
# ============================================================

async def is_clickable(element):

    try:

        if not await element.is_visible():
            return False

        tag = await get_tag_name(
            element
        )

        role = normalize_text(
            await get_attribute(
                element,
                "role"
            )
        )

        tabindex = await get_attribute(
            element,
            "tabindex"
        )

        disabled = await get_attribute(
            element,
            "disabled"
        )

        aria_disabled = normalize_text(
            await get_attribute(
                element,
                "aria-disabled"
            )
        )

        if disabled != "":
            return False

        if aria_disabled == "true":
            return False

        if tag in {
            "button",
            "a"
        }:
            return True

        if tag == "input":

            input_type = normalize_text(
                await get_attribute(
                    element,
                    "type"
                )
            )

            if input_type in {
                "button",
                "submit",
                "image"
            }:
                return True

        if role in {
            "button",
            "link"
        }:
            return True

        if tabindex == "0":
            return True

    except Exception:
        pass

    return False


# ============================================================
# FIND CLICKABLE ANCESTOR
# ============================================================

async def find_clickable_ancestor(
    element,
    max_levels=10
):

    current = element

    for level in range(max_levels):

        try:

            if await is_clickable(
                current
            ):

                print(
                    f"[NAV] Clickable ancestor "
                    f"found at level {level}"
                )

                await debug_element(
                    current,
                    f"CLICKABLE ANCESTOR LEVEL {level}"
                )

                return current

        except Exception:
            pass

        try:

            parent = current.locator(
                ".."
            )

            if await parent.count() == 0:
                break

            current = parent

        except Exception:
            break

    return None


# ============================================================
# GOOGLE FORMS NAVIGATION
#
# Google Forms structure:
#
# <div role="button" tabindex="0">
#     ...
#     <span>Next</span>
# </div>
#
# IMPORTANT:
# We directly target the OUTER role="button".
# ============================================================

async def find_google_forms_navigation(page):

    print(
        "\n========== GOOGLE FORMS NAVIGATION =========="
    )

    google_labels = [

        ("Next", "next"),
        ("Continue", "next"),
        ("Proceed", "next"),
        ("Next step", "next"),
        ("Save and continue", "next"),
        ("Save & continue", "next"),
        ("Review", "next"),

        ("Submit", "submit"),
        ("Submit application", "submit"),
        ("Apply", "submit"),
        ("Apply now", "submit"),
        ("Finish", "submit"),
        ("Complete", "submit"),
    ]

    # ========================================================
    # METHOD 1
    # DIRECT ROLE BUTTON + TEXT
    # ========================================================

    for label, action in google_labels:

        try:

            locator = page.locator(
                '[role="button"]'
            ).filter(
                has_text=re.compile(
                    rf"^\s*{re.escape(label)}\s*$",
                    re.IGNORECASE
                )
            )

            count = await locator.count()

            print(
                f"[GFORM] role=button "
                f"text='{label}' "
                f"candidates={count}"
            )

            for i in range(count):

                button = locator.nth(i)

                try:

                    visible = await button.is_visible()

                    print(
                        f"[GFORM] candidate={i} "
                        f"visible={visible}"
                    )

                    if not visible:
                        continue

                    await debug_element(
                        button,
                        f"GFORM ROLE BUTTON '{label}'"
                    )

                    if not await is_clickable(
                        button
                    ):

                        print(
                            f"[GFORM] candidate={i} "
                            f"is NOT clickable"
                        )

                        continue

                    print(
                        f"[GFORM] ✅ ACTUAL ROLE BUTTON "
                        f"FOUND: '{label}'"
                    )

                    print(
                        f"[GFORM] action = {action}"
                    )

                    return button, action

                except Exception as e:

                    print(
                        f"[GFORM] candidate={i} "
                        f"inspection failed: {e}"
                    )

        except Exception as e:

            print(
                f"[GFORM] role search failed "
                f"for '{label}': {e}"
            )

    # ========================================================
    # METHOD 2
    # GOOGLE jsname
    # ========================================================

    try:

        locator = page.locator(
            '[jsname="OCpkoe"]'
        )

        count = await locator.count()

        print(
            f"[GFORM] jsname=OCpkoe "
            f"candidates={count}"
        )

        for i in range(count):

            element = locator.nth(i)

            if not await element.is_visible():
                continue

            text = await get_element_text(
                element
            )

            action = classify_navigation(
                text
            )

            print(
                f"[GFORM] jsname candidate "
                f"{i}: text={text!r} "
                f"action={action}"
            )

            if action:

                await debug_element(
                    element,
                    "GFORM JSNAME BUTTON"
                )

                return element, action

    except Exception as e:

        print(
            f"[GFORM] jsname detection failed: {e}"
        )

    # ========================================================
    # METHOD 3
    # TEXT → CLICKABLE PARENT
    # ========================================================

    for label, action in google_labels:

        try:

            text_locator = page.get_by_text(
                label,
                exact=True
            )

            count = await text_locator.count()

            print(
                f"[GFORM] text fallback "
                f"'{label}' candidates={count}"
            )

            for i in range(count):

                text_element = (
                    text_locator.nth(i)
                )

                if not await text_element.is_visible():
                    continue

                clickable = (
                    await find_clickable_ancestor(
                        text_element,
                        max_levels=10
                    )
                )

                if clickable:

                    print(
                        f"[GFORM] ✅ Found clickable "
                        f"ancestor for '{label}'"
                    )

                    return (
                        clickable,
                        action
                    )

        except Exception as e:

            print(
                f"[GFORM] text fallback "
                f"failed for '{label}': {e}"
            )

    return None, None


# ============================================================
# NORMAL BUTTON DETECTION
# ============================================================

async def find_normal_buttons(page):

    print(
        "\n========== NORMAL BUTTON SCAN =========="
    )

    selector = """
        button,
        input[type="button"],
        input[type="submit"],
        input[type="image"],
        a[role="button"],
        a[href],
        [role="button"]
    """

    locator = page.locator(
        selector
    )

    try:
        count = await locator.count()
    except Exception:
        return None, None

    print(
        f"[NORMAL] candidates={count}"
    )

    candidates = []

    for i in range(count):

        element = locator.nth(i)

        try:

            if not await element.is_visible():
                continue

            text = await get_element_text(
                element
            )

            action = classify_navigation(
                text
            )

            if action:

                print(
                    f"[NORMAL] candidate {i}: "
                    f"{text!r} -> {action}"
                )

                candidates.append(
                    (
                        element,
                        action
                    )
                )

        except Exception:
            continue

    if candidates:

        return candidates[0]

    return None, None


# ============================================================
# MAIN NAVIGATION FINDER
# ============================================================

async def find_next_button(page):

    print(
        "\n"
        "===================================================="
    )

    print(
        "        NAVIGATION DETECTION START"
    )

    print(
        "===================================================="
    )

    # ========================================================
    # FIRST: GOOGLE FORMS
    # ========================================================

    element, action = (
        await find_google_forms_navigation(
            page
        )
    )

    if element:

        print(
            f"\n[NAV] ✅ GOOGLE FORMS "
            f"NAVIGATION FOUND: {action.upper()}"
        )

        await debug_element(
            element,
            "FINAL SELECTED NAVIGATION ELEMENT"
        )

        return element, action

    # ========================================================
    # SECOND: NORMAL BUTTONS
    # ========================================================

    element, action = (
        await find_normal_buttons(
            page
        )
    )

    if element:

        print(
            f"\n[NAV] ✅ NORMAL NAVIGATION "
            f"FOUND: {action.upper()}"
        )

        await debug_element(
            element,
            "FINAL NORMAL NAVIGATION ELEMENT"
        )

        return element, action

    # ========================================================
    # THIRD: EXACT TEXT FALLBACK
    # ========================================================

    print(
        "\n[NAV] Trying generic exact-text fallback..."
    )

    navigation_texts = [

        ("Next", "next"),
        ("Continue", "next"),
        ("Proceed", "next"),
        ("Next step", "next"),
        ("Continue application", "next"),
        ("Save and continue", "next"),
        ("Save & continue", "next"),
        ("Review", "next"),

        ("Submit", "submit"),
        ("Submit application", "submit"),
        ("Apply", "submit"),
        ("Apply now", "submit"),
        ("Finish", "submit"),
        ("Complete", "submit"),
    ]

    for text, action in navigation_texts:

        try:

            locator = page.get_by_text(
                text,
                exact=True
            )

            count = await locator.count()

            print(
                f"[NAV] exact text "
                f"'{text}' count={count}"
            )

            for i in range(count):

                text_element = locator.nth(i)

                if not await text_element.is_visible():
                    continue

                clickable = (
                    await find_clickable_ancestor(
                        text_element,
                        max_levels=10
                    )
                )

                if clickable:

                    print(
                        f"[NAV] ✅ exact-text "
                        f"fallback found: {action}"
                    )

                    return (
                        clickable,
                        action
                    )

        except Exception as e:

            print(
                f"[NAV] exact text "
                f"'{text}' failed: {e}"
            )

    print(
        "\n[NAV] ❌ NO NAVIGATION BUTTON FOUND"
    )

    return None, None


# ============================================================
# PAGE STATE
# ============================================================

async def get_page_state(page):

    try:
        url = page.url
    except Exception:
        url = ""

    try:
        body = await page.locator(
            "body"
        ).inner_text()
    except Exception:
        body = ""

    return url, body


# ============================================================
# GOOGLE FORMS STATE
# ============================================================

async def get_google_forms_state(page):

    try:

        buttons = page.locator(
            '[role="button"]'
        )

        count = await buttons.count()

        visible_buttons = []

        for i in range(count):

            button = buttons.nth(i)

            try:

                if not await button.is_visible():
                    continue

                text = await get_element_text(
                    button
                )

                if text:
                    visible_buttons.append(
                        text
                    )

            except Exception:
                continue

        try:
            body = await page.locator(
                "body"
            ).inner_text()
        except Exception:
            body = ""

        return (
            normalize_text(body),
            tuple(visible_buttons)
        )

    except Exception:

        return "", ()


# ============================================================
# WAIT FOR NORMAL PAGE CHANGE
# ============================================================

async def wait_for_navigation_change(
    page,
    before_url,
    before_text,
    timeout=8000
):

    print(
        "[NAV] Waiting for page state change..."
    )

    start = (
        asyncio.get_event_loop().time()
    )

    while True:

        try:
            current_url = page.url
        except Exception:
            current_url = ""

        try:
            current_text = (
                await page.locator(
                    "body"
                ).inner_text()
            )
        except Exception:
            current_text = ""

        if current_url != before_url:

            print(
                "[NAV] ✅ URL changed"
            )

            return True

        if current_text != before_text:

            print(
                "[NAV] ✅ Body text changed"
            )

            return True

        elapsed = (
            asyncio.get_event_loop().time()
            - start
        )

        if elapsed >= timeout / 1000:
            break

        await asyncio.sleep(
            0.25
        )

    print(
        "[NAV] No normal page-state change detected"
    )

    return False


# ============================================================
# VERIFY GOOGLE FORMS NAVIGATION
# ============================================================

async def verify_google_forms_navigation(
    page,
    before_body,
    before_buttons,
    timeout=7000
):

    print(
        "[GFORM VERIFY] Checking whether "
        "Google Forms actually moved..."
    )

    start = (
        asyncio.get_event_loop().time()
    )

    while True:

        try:

            after_body, after_buttons = (
                await get_google_forms_state(
                    page
                )
            )

            success_indicators = [

                "your response has been recorded",

                "response has been recorded",

                "thank you for submitting",

                "thank you for your response",

                "application submitted",

                "successfully submitted",

                "submission received",
            ]

            for indicator in success_indicators:

                if indicator in after_body:

                    print(
                        f"[GFORM VERIFY] ✅ "
                        f"Submission detected: "
                        f"{indicator}"
                    )

                    return True

            if after_body != before_body:

                print(
                    "[GFORM VERIFY] ✅ "
                    "Google Forms body changed"
                )

                return True

            if after_buttons != before_buttons:

                print(
                    "[GFORM VERIFY] ✅ "
                    "Google Forms navigation "
                    "state changed"
                )

                return True

        except Exception as e:

            print(
                f"[GFORM VERIFY] "
                f"verification error: {e}"
            )

        elapsed = (
            asyncio.get_event_loop().time()
            - start
        )

        if elapsed >= timeout / 1000:
            break

        await asyncio.sleep(
            0.25
        )

    print(
        "[GFORM VERIFY] ❌ "
        "No state change detected"
    )

    return False


# ============================================================
# GOOGLE FORMS CLICK
# ============================================================

async def click_google_forms_button(
    page,
    element
):

    print(
        "\n========== GOOGLE FORMS CLICK =========="
    )

    await debug_element(
        element,
        "ELEMENT WE ARE ABOUT TO CLICK"
    )

    # ========================================================
    # ENSURE ACTUAL ROLE BUTTON
    # ========================================================

    try:

        role = normalize_text(
            await element.get_attribute(
                "role"
            )
        )

        text = await get_element_text(
            element
        )

        print(
            f"[GFORM CLICK] role={role!r}"
        )

        print(
            f"[GFORM CLICK] text={text!r}"
        )

        if role != "button":

            print(
                "[GFORM CLICK] Selected element "
                "is not role=button."
            )

            resolved = (
                await find_clickable_ancestor(
                    element,
                    max_levels=10
                )
            )

            if resolved:

                print(
                    "[GFORM CLICK] Resolved actual "
                    "clickable ancestor."
                )

                element = resolved

                await debug_element(
                    element,
                    "RESOLVED ROLE BUTTON"
                )

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"Role verification error: {e}"
        )

    # ========================================================
    # SCROLL
    # ========================================================

    try:

        print(
            "[GFORM CLICK] Scrolling button "
            "into view..."
        )

        await element.scroll_into_view_if_needed(
            timeout=5000
        )

        await asyncio.sleep(
            0.3
        )

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"Scroll failed: {e}"
        )

    # ========================================================
    # HOVER
    # ========================================================

    try:

        print(
            "[GFORM CLICK] Hovering..."
        )

        await element.hover(
            timeout=3000
        )

    except Exception as e:

        print(
            f"[GFORM CLICK] Hover skipped: {e}"
        )

    # ========================================================
    # METHOD 1
    # NORMAL CLICK
    # ========================================================

    try:

        print(
            "[GFORM CLICK] "
            "METHOD 1: Playwright click()"
        )

        await element.click(
            timeout=7000
        )

        print(
            "[GFORM CLICK] "
            "✅ METHOD 1 CLICK EXECUTED"
        )

        return True

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"❌ METHOD 1 FAILED: {e}"
        )

    # ========================================================
    # METHOD 2
    # FORCE CLICK
    # ========================================================

    try:

        print(
            "[GFORM CLICK] "
            "METHOD 2: force=True"
        )

        await element.click(
            force=True,
            timeout=5000
        )

        print(
            "[GFORM CLICK] "
            "✅ METHOD 2 CLICK EXECUTED"
        )

        return True

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"❌ METHOD 2 FAILED: {e}"
        )

    # ========================================================
    # METHOD 3
    # ENTER
    # ========================================================

    try:

        print(
            "[GFORM CLICK] "
            "METHOD 3: focus + Enter"
        )

        await element.focus()

        await asyncio.sleep(
            0.2
        )

        await element.press(
            "Enter"
        )

        print(
            "[GFORM CLICK] "
            "✅ METHOD 3 ENTER EXECUTED"
        )

        return True

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"❌ METHOD 3 FAILED: {e}"
        )

    # ========================================================
    # METHOD 4
    # SPACE
    # ========================================================

    try:

        print(
            "[GFORM CLICK] "
            "METHOD 4: focus + Space"
        )

        await element.focus()

        await element.press(
            "Space"
        )

        print(
            "[GFORM CLICK] "
            "✅ METHOD 4 SPACE EXECUTED"
        )

        return True

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"❌ METHOD 4 FAILED: {e}"
        )

    # ========================================================
    # METHOD 5
    # JAVASCRIPT CLICK
    # ========================================================

    try:

        print(
            "[GFORM CLICK] "
            "METHOD 5: JavaScript click()"
        )

        await element.evaluate(
            """
            el => {

                el.scrollIntoView({
                    behavior: "instant",
                    block: "center",
                    inline: "center"
                });

                el.click();
            }
            """
        )

        print(
            "[GFORM CLICK] "
            "✅ METHOD 5 JS CLICK EXECUTED"
        )

        return True

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"❌ METHOD 5 FAILED: {e}"
        )

    # ========================================================
    # METHOD 6
    # REAL MOUSE CLICK
    # ========================================================

    try:

        print(
            "[GFORM CLICK] "
            "METHOD 6: mouse coordinate click"
        )

        box = await element.bounding_box()

        if not box:

            raise RuntimeError(
                "No bounding box available"
            )

        x = (
            box["x"]
            + box["width"] / 2
        )

        y = (
            box["y"]
            + box["height"] / 2
        )

        print(
            f"[GFORM CLICK] "
            f"Clicking coordinates "
            f"x={x:.2f}, y={y:.2f}"
        )

        await page.mouse.move(
            x,
            y
        )

        await asyncio.sleep(
            0.15
        )

        await page.mouse.down()

        await asyncio.sleep(
            0.1
        )

        await page.mouse.up()

        print(
            "[GFORM CLICK] "
            "✅ METHOD 6 MOUSE CLICK EXECUTED"
        )

        return True

    except Exception as e:

        print(
            f"[GFORM CLICK] "
            f"❌ METHOD 6 FAILED: {e}"
        )

    print(
        "[GFORM CLICK] "
        "❌ ALL GOOGLE FORMS CLICK METHODS FAILED"
    )

    return False


# ============================================================
# CLICK NAVIGATION
# ============================================================

async def click_navigation(
    page,
    element,
    action
):

    print(
        "\n"
        "===================================================="
    )

    print(
        f"       CLICK NAVIGATION: "
        f"{action.upper()}"
    )

    print(
        "===================================================="
    )

    if element is None:

        print(
            "[NAV CLICK] ❌ element is None"
        )

        return False

    # ========================================================
    # DEBUG SELECTED ELEMENT
    # ========================================================

    await debug_element(
        element,
        "SELECTED NAVIGATION ELEMENT"
    )

    # ========================================================
    # CAPTURE STATE
    # ========================================================

    before_url, before_text = (
        await get_page_state(
            page
        )
    )

    before_google_body, before_buttons = (
        await get_google_forms_state(
            page
        )
    )

    print(
        f"[NAV CLICK] before URL = "
        f"{before_url}"
    )

    print(
        f"[NAV CLICK] before body length = "
        f"{len(before_text)}"
    )

    print(
        f"[NAV CLICK] before Google buttons = "
        f"{before_buttons}"
    )

    # ========================================================
    # DETECT GOOGLE BUTTON
    # ========================================================

    try:

        role = normalize_text(
            await element.get_attribute(
                "role"
            )
        )

        jsname = await element.get_attribute(
            "jsname"
        )

        is_google_button = (
            role == "button"
            or jsname == "OCpkoe"
        )

    except Exception:

        is_google_button = False

    # ========================================================
    # GOOGLE FORMS
    # ========================================================

    if is_google_button:

        print(
            "[NAV CLICK] "
            "🔥 GOOGLE FORMS BUTTON DETECTED"
        )

        clicked = (
            await click_google_forms_button(
                page,
                element
            )
        )

        if not clicked:

            print(
                "[NAV CLICK] "
                "❌ Google Forms click failed"
            )

            return False

    # ========================================================
    # NORMAL FORM
    # ========================================================

    else:

        print(
            "[NAV CLICK] "
            "Normal HTML navigation button"
        )

        try:

            await element.scroll_into_view_if_needed(
                timeout=5000
            )

        except Exception:
            pass

        try:

            await element.click(
                timeout=7000
            )

            print(
                "[NAV CLICK] "
                "✅ Normal click executed"
            )

        except Exception as e:

            print(
                f"[NAV CLICK] "
                f"Normal click failed: {e}"
            )

            try:

                await element.click(
                    force=True,
                    timeout=5000
                )

                print(
                    "[NAV CLICK] "
                    "✅ Force click executed"
                )

            except Exception as e2:

                print(
                    f"[NAV CLICK] "
                    f"Force click failed: {e2}"
                )

                return False

    # ========================================================
    # WAIT FOR EVENT
    # ========================================================

    print(
        "[NAV CLICK] "
        "Waiting for click event..."
    )

    await asyncio.sleep(
        0.8
    )

    # ========================================================
    # GOOGLE VERIFICATION
    # ========================================================

    if is_google_button:

        verified = (
            await verify_google_forms_navigation(
                page,
                before_google_body,
                before_buttons,
                timeout=7000
            )
        )

        if verified:

            print(
                "\n[NAV CLICK] "
                "🎉 GOOGLE FORMS NAVIGATION "
                "SUCCESSFUL"
            )

            return True

        print(
            "\n[NAV CLICK] "
            "⚠️ Click executed but "
            "navigation was not verified."
        )

        print(
            "[NAV CLICK] Re-scanning current page..."
        )

        current_element, current_action = (
            await find_google_forms_navigation(
                page
            )
        )

        if current_element:

            print(
                f"[NAV CLICK] Current navigation "
                f"after click: {current_action}"
            )

            if (
                action == "next"
                and current_action == "submit"
            ):

                print(
                    "[NAV CLICK] "
                    "✅ Next → Submit transition "
                    "detected"
                )

                return True

        print(
            "[NAV CLICK] "
            "❌ Unable to verify Google Forms "
            "navigation."
        )

        return False

    # ========================================================
    # NORMAL FORM VERIFICATION
    # ========================================================

    changed = (
        await wait_for_navigation_change(
            page,
            before_url,
            before_text,
            timeout=6000
        )
    )

    if changed:

        print(
            "[NAV CLICK] "
            "✅ Normal navigation successful"
        )

        return True

    # ========================================================
    # SUBMISSION INDICATORS
    # ========================================================

    try:

        body = (
            await page.locator(
                "body"
            ).inner_text()
        ).lower()

    except Exception:

        body = ""

    success_indicators = [

        "your response has been recorded",

        "response has been recorded",

        "thank you for submitting",

        "thank you for your response",

        "application submitted",

        "successfully submitted",

        "submission received",
    ]

    for indicator in success_indicators:

        if indicator in body:

            print(
                f"[NAV CLICK] "
                f"✅ Submission indicator: "
                f"{indicator}"
            )

            return True

    print(
        "[NAV CLICK] "
        "⚠️ Click executed but "
        "state change could not be verified."
    )

    return True