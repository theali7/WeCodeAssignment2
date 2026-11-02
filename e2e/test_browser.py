"""Real Chromium -> Docker app -> PostgreSQL. No mocked auth or progress responses.

Run only against a disposable assignment stack populated by e2e/seed.py.
Separate runtime acceptance checks live in runtime_acceptance.py and remain failing
until the missing captured language workers are restored (issues #18 and #21).
"""
import json
import os
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("WECODE_E2E_URL", "http://localhost:8080").rstrip("/")
PASSWORD = "Disposable-e2e-password-42"
ARTIFACTS = Path("e2e-results")


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("WECODE_DISPOSABLE_E2E") != "yes":
            raise RuntimeError("E2E requires an explicitly disposable stack")
        if urlsplit(BASE).hostname not in {"localhost", "127.0.0.1", "web"}:
            raise RuntimeError("Refusing to test a non-local host")
        ARTIFACTS.mkdir(exist_ok=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.api = cls.pw.request.new_context(base_url=BASE)
        health = cls.api.get("/api/health")
        assert health.ok and health.json()["database"] == "postgresql"
        expect.set_options(timeout=12000)

    @classmethod
    def tearDownClass(cls):
        cls.api.dispose()
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.contexts = []
        self.external = []
        self.new_context()
        self.email = f"e2e-{uuid4().hex}@example.invalid"

    def new_context(self):
        self.context = self.browser.new_context(viewport={"width":1440,"height":1000})
        self.contexts.append(self.context)
        self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        def guard(route):
            host = urlsplit(route.request.url).hostname
            if host and host != urlsplit(BASE).hostname:
                self.external.append(route.request.url)
                route.abort()
            else:
                route.continue_()
        self.context.route("**/*", guard)
        self.page = self.context.new_page()
        self.page.set_default_timeout(12000)
        return self.page

    def tearDown(self):
        # Always capture artifacts so any failed locator has visible evidence.
        stem = self._testMethodName
        for index, context in enumerate(self.contexts):
            for page in context.pages:
                if not page.is_closed():
                    page.screenshot(path=str(ARTIFACTS / f"{stem}-{index}.png"), full_page=True)
                    (ARTIFACTS / f"{stem}-{index}.txt").write_text(page.locator("body").inner_text())
            context.tracing.stop(path=str(ARTIFACTS / f"{stem}-{index}.zip"))
            context.close()
        self.assertEqual(self.external, [], "Browser attempted external network access")

    def account(self):
        response = self.api.post("/api/auth/v1/signup", data={
            "email":self.email, "password":PASSWORD, "data":{"display_name":"E2E learner"}})
        self.assertEqual(response.status, 200, response.text())
        self.session = response.json()

    def login(self, password=PASSWORD):
        self.page.goto(BASE)
        self.page.locator(".header-actions").get_by_role("button", name="Log in", exact=True).click()
        panel = self.page.locator(".account-panel")
        panel.get_by_label("Email", exact=True).fill(self.email)
        panel.get_by_label("Password", exact=True).fill(password)
        panel.get_by_role("button", name="Log in", exact=True).click()
        if password == PASSWORD:
            self.workspace()

    def workspace(self):
        expect(self.page.get_by_role("button", name=re.compile("Sign out"))).to_be_visible()
        expect(self.page.get_by_label("Search problems", exact=True)).to_be_visible()

    def signed_in(self):
        self.account()
        self.login()

    def nav(self, label):
        self.page.get_by_role("navigation", name="Your learning space", exact=True).get_by_role(
            "button", name=re.compile("^" + re.escape(label))).click()

    def overview(self):
        self.page.get_by_role("button", name="Overview", exact=True).click()
        expect(self.page.locator(".campus-table tbody tr")).to_have_count(4)

    def filter(self, label, value):
        self.page.get_by_role("button", name=re.compile("^"+re.escape(label)+":")).click()
        self.page.get_by_role("option", name=value, exact=True).click()

    def open_problem(self, number=1):
        self.page.locator(f"#problem-{number}").click()
        expect(self.page.locator(".cm-content")).to_be_visible()

    def test_01_landing_and_mobile_menu(self):  # #11
        self.page.goto(BASE)
        expect(self.page.locator("h1")).to_contain_text("Learn to code.")
        for title, anchor in [("Learning paths","paths"),("Algorithms","algorithms"),
                              ("Challenges","practice"),("Projects","projects")]:
            self.page.get_by_role("navigation",name="Main navigation").get_by_role("link",name=title,exact=True).click()
            expect(self.page).to_have_url(re.compile("#"+anchor+"$"))
        self.page.set_viewport_size({"width":390,"height":844})
        menu = self.page.get_by_role("button",name="Open menu",exact=True)
        menu.click()
        expect(self.page.locator("#mobile-nav")).to_be_visible()
        self.page.locator("#mobile-nav").get_by_role("link",name="Algorithms",exact=True).click()
        expect(self.page.locator("#mobile-nav")).to_have_count(0)

    def test_02_signup_validation_success_duplicate(self):  # #12
        self.page.goto(BASE)
        self.page.locator(".header-actions").get_by_role("button",name=re.compile("Sign up")).click()
        panel = self.page.locator(".account-panel")
        panel.get_by_role("button",name="Create account",exact=True).click()
        self.assertFalse(panel.locator("form").evaluate("form => form.checkValidity()"))
        panel.get_by_label("Name",exact=True).fill("E2E learner")
        panel.get_by_label("Email",exact=True).fill("invalid-email")
        panel.get_by_label("Password",exact=True).fill("short")
        self.assertFalse(panel.locator("form").evaluate("form => form.checkValidity()"))
        panel.get_by_label("Email",exact=True).fill(self.email)
        self.assertFalse(panel.locator("form").evaluate("form => form.checkValidity()"))
        panel.get_by_label("Password",exact=True).fill(PASSWORD)
        panel.get_by_role("button",name="Create account",exact=True).click()
        self.workspace()
        self.page.get_by_role("button",name=re.compile("Sign out")).click()
        self.page.locator(".header-actions").get_by_role("button",name=re.compile("Sign up")).click()
        panel.get_by_label("Name",exact=True).fill("E2E learner")
        panel.get_by_label("Email",exact=True).fill(self.email)
        panel.get_by_label("Password",exact=True).fill(PASSWORD)
        panel.get_by_role("button",name="Create account",exact=True).click()
        expect(panel.get_by_role("alert")).to_contain_text(re.compile("already",re.I))

    def test_03_login_refresh_logout(self):  # #13
        self.account()
        self.login("wrong-password")
        expect(self.page.locator(".account-panel").get_by_role("alert")).to_contain_text(re.compile("invalid",re.I))
        self.page.locator(".account-panel").get_by_label("Password",exact=True).fill(PASSWORD)
        self.page.locator(".account-panel").get_by_role("button",name="Log in",exact=True).click()
        self.workspace()
        self.page.reload()
        self.workspace()
        self.page.get_by_role("button",name=re.compile("Sign out")).click()
        expect(self.page.locator(".header-actions").get_by_role("button",name="Log in",exact=True)).to_be_visible()
        self.page.reload()
        expect(self.page.get_by_label("Search problems",exact=True)).to_have_count(0)
        self.new_context()
        self.login()

    def test_04_preferences_persist_in_fresh_context(self):  # #14
        self.signed_in()
        for language, level in [("java","1"),("python","2"),("sql","0")]:
            self.page.get_by_role("button",name="Edit your learning preferences",exact=True).click()
            dialog=self.page.get_by_role("dialog")
            dialog.get_by_label("Display name",exact=True).fill("Updated E2E")
            dialog.get_by_label("My focus",exact=True).select_option(language)
            dialog.get_by_label("Experience",exact=True).select_option(level)
            dialog.get_by_role("button",name=re.compile("Save preferences")).click()
            expect(dialog).to_have_count(0)
            self.page.reload()
            self.workspace()
        self.new_context()
        self.login()
        self.page.get_by_role("button",name="Edit your learning preferences",exact=True).click()
        dialog=self.page.get_by_role("dialog")
        expect(dialog.get_by_label("Display name",exact=True)).to_have_value("Updated E2E")
        expect(dialog.get_by_label("My focus",exact=True)).to_have_value("sql")
        expect(dialog.get_by_label("Experience",exact=True)).to_have_value("0")
        dialog.get_by_label("Display name",exact=True).press("Escape")
        expect(dialog).to_have_count(0)

    def test_05_problem_catalog_filters(self):  # #15
        self.signed_in()
        rows=self.page.locator(".problem-table tbody tr")
        expect(rows).to_have_count(108)
        self.page.get_by_label("Search problems",exact=True).fill("nonexistent-zzzz")
        expect(self.page.get_by_role("heading",name="No matching problems.",exact=True)).to_be_visible()
        self.page.get_by_role("button",name="Reset filters",exact=True).click()
        expect(rows).to_have_count(108)
        for language in ["Python","Java","SQL"]:
            self.page.get_by_role("group",name="Problem language",exact=True).get_by_role("button",name=language,exact=True).click()
            expect(rows.first).to_be_visible()
            self.assertTrue(all(language in text for text in rows.locator("td:nth-child(4)").all_text_contents()))
        self.page.get_by_role("button",name="Reset filters",exact=True).click()
        self.filter("Difficulty","Easy")
        expect(rows.first).to_be_visible()
        self.assertEqual(set(rows.locator(".problem-difficulty").all_text_contents()),{"Easy"})
        self.filter("Topic","Arrays")
        self.assertEqual(set(rows.locator(".problem-topic").all_text_contents()),{"Arrays"})
        self.filter("Sort by","Title A–Z")
        titles=rows.locator("td:nth-child(2)").all_text_contents()
        self.assertEqual(titles, sorted(titles, key=str.casefold))

    def test_06_problem_detail_navigation_resize(self):  # #16
        self.signed_in()
        self.open_problem()
        expect(self.page.get_by_role("heading",name="Sum of the positive values",exact=True)).to_be_visible()
        expect(self.page.get_by_role("button",name="Previous problem",exact=True)).to_be_disabled()
        self.page.get_by_role("button",name="Next problem",exact=True).click()
        expect(self.page.get_by_role("heading",name="Running study totals",exact=True)).to_be_visible()
        self.page.get_by_role("button",name="Previous problem",exact=True).click()
        splitter=self.page.get_by_role("separator").first
        before=splitter.get_attribute("aria-valuenow")
        splitter.press("ArrowRight")
        self.assertNotEqual(splitter.get_attribute("aria-valuenow"),before)
        self.page.get_by_role("button",name=re.compile("Problem list")).click()
        expect(self.page.get_by_label("Search problems",exact=True)).to_be_visible()

    def test_07_editor_draft_survives_reopen(self):  # #17
        self.signed_in()
        self.open_problem()
        self.page.get_by_role("group",name="Editor language",exact=True).get_by_role("button",name="Python",exact=True).click()
        editor=self.page.locator(".cm-content")
        editor.fill("def solve(values):\n    return sum(x for x in values if x > 0)\n")
        # Wait for the UI's debounced storage, not an arbitrary sleep.
        self.page.wait_for_function("() => Object.keys(localStorage).some(k => k.includes('draft') && (localStorage.getItem(k)||'').includes('return sum'))")
        self.page.get_by_role("button",name=re.compile("Problem list")).click()
        self.open_problem()
        self.page.get_by_role("group",name="Editor language",exact=True).get_by_role("button",name="Python",exact=True).click()
        expect(editor).to_contain_text("return sum")
        self.page.reload()
        self.workspace()
        self.open_problem()
        self.page.get_by_role("group",name="Editor language",exact=True).get_by_role("button",name="Python",exact=True).click()
        expect(editor).to_contain_text("return sum")

    def test_08_learn_languages(self):  # #19
        self.signed_in()
        for language in ["Java","Python","SQL"]:
            self.nav("Learn Languages")
            card=self.page.get_by_role("group",name="Choose a language to explore",exact=True).get_by_role("button",name=re.compile(language))
            card.click()
            expect(card).to_have_attribute("aria-pressed","true")
            expect(self.page.locator(".ll-example code")).not_to_be_empty()
            expect(self.page.locator(".ll-language-footer a")).to_have_attribute("href",re.compile("^https://"))
            self.page.get_by_role("button",name=re.compile("View "+language+" lessons")).click()
            expect(self.page.get_by_label("Language",exact=True)).to_have_value(language.lower())
            expect(self.page.locator(".campus-table tbody tr").first).to_contain_text(language)

    def test_09_learning_notes_persist_without_browser_storage(self):  # #20
        self.signed_in()
        for language in ["Java","Python","SQL"]:
            self.nav("Learning way")
            self.page.get_by_role("group",name="Learning language",exact=True).get_by_role("button",name=re.compile("^"+language)).click()
            expect(self.page.locator(".lw-route-topic").first).to_be_enabled()
            self.page.locator(".lw-route-topic").first.click()
            expect(self.page.get_by_role("heading",name="Worked example",exact=True)).to_be_visible()
            expect(self.page.get_by_role("button",name=re.compile("02 · Practice"))).to_be_disabled()
            self.page.get_by_role("button",name=re.compile("I have read the notes")).click()
            expect(self.page.locator(".lw-task-list > button")).to_have_count(5)
            expect(self.page.get_by_text("Progress synced with your account",exact=False).first).to_be_visible()
        self.new_context()
        self.login()
        self.nav("Learning way")
        self.page.get_by_role("group",name="Learning language",exact=True).get_by_role("button",name=re.compile("^SQL")).click()
        expect(self.page.locator(".lw-route-topic").first).to_contain_text("Notes read")

    def test_10_library_filters_and_empty_state(self):  # #22
        self.signed_in()
        self.overview()
        search=self.page.get_by_label("Search materials",exact=True)
        search.fill("nonexistent-zzzz")
        expect(self.page.get_by_role("heading",name="No materials found.",exact=True)).to_be_visible()
        search.fill("E2E")
        self.page.get_by_label("Language",exact=True).select_option("java")
        expect(self.page.locator(".campus-table tbody tr")).to_have_count(1)
        self.page.get_by_label("Status",exact=True).select_option("completed")
        expect(self.page.locator(".campus-table tbody tr")).to_have_count(0)
        self.page.get_by_label("Status",exact=True).select_option("incomplete")
        expect(self.page.locator(".campus-table tbody tr")).to_have_count(1)

    def test_11_lesson_completion_fresh_login_and_isolation(self):  # #23
        self.signed_in()
        self.overview()
        self.page.locator(".campus-material").filter(has_text="E2E Java foundations").click()
        expect(self.page.locator(".campus-reader")).to_contain_text("A disposable lesson")
        self.page.get_by_role("button",name=re.compile("Mark as complete")).click()
        expect(self.page.get_by_role("button",name="Completed",exact=True)).to_be_disabled()
        self.new_context()
        self.login()
        self.overview()
        row=self.page.locator(".campus-table tbody tr").filter(has_text="E2E Java foundations")
        expect(row).to_contain_text("Completed")
        expect(self.page.get_by_role("progressbar",name="Learning progress",exact=True)).to_have_attribute("aria-valuenow","25")
        self.new_context()
        self.email=f"e2e-{uuid4().hex}@example.invalid"
        self.account()
        self.login()
        self.overview()
        expect(self.page.get_by_role("progressbar",name="Learning progress",exact=True)).to_have_attribute("aria-valuenow","0")

    def test_12_bookmarks_saved_materials(self):  # #24
        self.signed_in()
        self.overview()
        self.page.get_by_role("button",name="Save E2E Java foundations",exact=True).click()
        self.nav("Saved materials")
        expect(self.page.locator(".campus-table tbody tr")).to_have_count(1)
        self.page.reload()
        self.workspace()
        self.nav("Saved materials")
        expect(self.page.locator(".campus-table tbody tr")).to_have_count(1)
        self.page.get_by_role("button",name="Unsave E2E Java foundations",exact=True).click()
        expect(self.page.get_by_role("heading",name="Keep good ideas close.",exact=True)).to_be_visible()

    def test_13_workspace_project_ideas(self):  # #25
        self.signed_in()
        self.nav("My progress")
        expect(self.page.get_by_role("progressbar",name="Learning progress",exact=True)).to_have_attribute("aria-valuenow","0")
        self.nav("Project Idea")
        expect(self.page.locator(".campus-idea-grid")).to_contain_text("A personal reading tracker")
        expect(self.page.locator(".campus-idea-grid")).to_contain_text("A study session analyzer")
        expect(self.page.locator(".campus-idea-grid")).to_contain_text("A learning activity report")
        self.page.get_by_role("button",name="Problems",exact=True).click()
        self.workspace()

    def test_14_disabled_providers_and_recovery(self):  # #26
        self.page.goto(BASE)
        self.page.locator(".header-actions").get_by_role("button",name="Log in",exact=True).click()
        panel=self.page.locator(".account-panel")
        for provider in ["Google","GitHub"]:
            expect(panel.get_by_role("button",name="Continue with "+provider,exact=True)).to_be_disabled()
        panel.get_by_role("button",name="Forgot password?",exact=True).click()
        panel.get_by_label("Email",exact=True).fill(self.email)
        panel.get_by_role("button",name="Reset password",exact=True).click()
        expect(panel.get_by_role("alert")).to_contain_text(re.compile("not configured|not available|not supported",re.I))
        expect(panel.get_by_role("status")).to_have_count(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
