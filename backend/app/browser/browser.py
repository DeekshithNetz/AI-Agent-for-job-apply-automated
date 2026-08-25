from playwright.async_api import async_playwright


class Browser:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=False
        )

        self.page = await self.browser.new_page(
            viewport={
                "width": 1440,
                "height": 900
            }
        )

    async def open(self, url: str):
        await self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await self.page.wait_for_timeout(2000)

    async def get_page_content(self):
        return await self.page.locator("body").inner_text()

    async def fill_field(self, description: str, value: str):
        """
        Try multiple strategies to find a form field.
        """

        if not value:
            return False

        # 1. Label
        try:
            locator = self.page.get_by_label(
                description,
                exact=False
            ).first

            if await locator.count() > 0:
                await locator.fill(value)
                return True

        except Exception:
            pass

        # 2. Placeholder
        try:
            locator = self.page.get_by_placeholder(
                description,
                exact=False
            ).first

            if await locator.count() > 0:
                await locator.fill(value)
                return True

        except Exception:
            pass

        # 3. Input containing matching attributes
        try:
            locator = self.page.locator(
                "input, textarea"
            )

            count = await locator.count()

            description_lower = description.lower()

            for i in range(count):

                element = locator.nth(i)

                attributes = await element.evaluate(
                    """
                    el => ({
                        name: el.name || "",
                        id: el.id || "",
                        placeholder: el.placeholder || "",
                        aria: el.getAttribute("aria-label") || ""
                    })
                    """
                )

                text = " ".join(
                    str(v).lower()
                    for v in attributes.values()
                )

                if description_lower in text or any(
                    word in text
                    for word in description_lower.split()
                    if len(word) > 3
                ):
                    await element.fill(value)
                    return True

        except Exception:
            pass

        return False

    async def upload_resume(self, resume_path: str):
        """
        Find a resume/CV file input and upload the resume.
        """

        inputs = self.page.locator(
            'input[type="file"]'
        )

        count = await inputs.count()

        if count == 0:
            return False

        for i in range(count):

            element = inputs.nth(i)

            try:
                attributes = await element.evaluate(
                    """
                    el => ({
                        name: el.name || "",
                        id: el.id || "",
                        accept: el.accept || "",
                        aria: el.getAttribute("aria-label") || ""
                    })
                    """
                )

                text = " ".join(
                    str(v).lower()
                    for v in attributes.values()
                )

                if (
                    "resume" in text
                    or "cv" in text
                    or "curriculum" in text
                    or "pdf" in text
                    or not text
                ):
                    await element.set_input_files(
                        resume_path
                    )

                    return True

            except Exception:
                continue

        return False

    async def check_consent(self):
        """
        Check normal consent/agreement checkboxes.
        """

        checkboxes = self.page.locator(
            'input[type="checkbox"]'
        )

        count = await checkboxes.count()

        for i in range(count):

            checkbox = checkboxes.nth(i)

            try:
                if not await checkbox.is_checked():
                    await checkbox.check()

            except Exception:
                pass

        return True

    async def click_next(self):
        """
        Try to move to the next page of a multi-page form.
        """

        possible_names = [
            "Next",
            "Continue",
            "Save and Continue",
            "Next Step"
        ]

        for name in possible_names:

            try:
                button = self.page.get_by_role(
                    "button",
                    name=name,
                    exact=False
                ).first

                if await button.count() > 0:
                    await button.click()
                    await self.page.wait_for_timeout(1500)
                    return True

            except Exception:
                pass

        return False

    async def submit(self):
        """
        Submit the application.
        """

        possible_names = [
            "Submit Application",
            "Submit",
            "Apply",
            "Send Application"
        ]

        for name in possible_names:

            try:
                button = self.page.get_by_role(
                    "button",
                    name=name,
                    exact=False
                ).first

                if await button.count() > 0:

                    await button.click()

                    await self.page.wait_for_timeout(3000)

                    return True

            except Exception:
                pass

        return False

    async def close(self):

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()