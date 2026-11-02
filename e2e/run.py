"""Run independent groups on separate disposable CI stacks, without relaxing auth limits."""
import os
import sys
import unittest
from e2e.test_browser import BrowserTests

index = int(os.environ.get("E2E_SHARD", "0"))
total = int(os.environ.get("E2E_SHARDS", "1"))
if not 1 <= total <= 10 or not 0 <= index < total:
    raise SystemExit("Invalid E2E shard")
names = unittest.defaultTestLoader.getTestCaseNames(BrowserTests)
suite = unittest.TestSuite(BrowserTests(name) for offset, name in enumerate(names) if offset % total == index)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
