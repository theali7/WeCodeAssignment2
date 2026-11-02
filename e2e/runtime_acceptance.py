"""Unfinished acceptance gate for #18; deliberately fails while workers are missing.

Run explicitly: python -m unittest e2e.runtime_acceptance -v
This is not part of the core suite and must not be reported as passing coverage.
"""
from e2e import test_browser as core
from playwright.sync_api import expect
import re


class RuntimeAcceptance(core.BrowserTests):
    # Inherit lifecycle/helpers without rerunning the core tests.
    for _name in list(vars(core.BrowserTests)):
        if _name.startswith("test_"):
            locals()[_name] = None

    def test_real_python_grading(self):
        worker = self.api.get("/runtimes/python.worker.mjs")
        self.assertTrue(worker.ok and "javascript" in worker.headers.get("content-type", ""),
                        "Missing Python worker: restore runtimes/ before claiming grading coverage (#18)")
        self.signed_in()
        self.open_problem()
        self.page.get_by_role("group",name="Editor language",exact=True).get_by_role("button",name="Python",exact=True).click()
        self.page.locator(".cm-content").fill("def solve(values):\n    return sum(x for x in values if x > 0)\n")
        self.page.get_by_role("button",name=re.compile("Submit")).click()
        expect(self.page.locator(".submission-report")).to_contain_text("Accepted",timeout=130000)
