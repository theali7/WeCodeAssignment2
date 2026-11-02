"""Wire the recovered browser build to the same-origin assignment API.

Keep the captured bundle intact in Git. Patch only the runtime copy in the image.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "assets/index-DXabLyQE.js"
source = path.read_text()
original = "var Ga=`https://oapnfhnvisujhrfdvklm.supabase.co`,Ka="
replacement = "var Ga=window.location.origin+`/api`,Ka="
if source.count(original) != 1:
    raise SystemExit("Expected exactly one original API configuration; refusing an unsafe patch")
workspace_path = root / "assets/problems-DIwfYwGF.js"
workspace = workspace_path.read_text()
old_language = "e.languages.includes(`Python`)?`Python`:`SQL`"
new_language = "e.languages.includes(`Python`)?`Python`:e.languages[0]"
if workspace.count(old_language) != 1:
    raise SystemExit("Expected one editor default; refusing an unsafe patch")
path.write_text(source.replace(original, replacement))
workspace_path.write_text(workspace.replace(old_language, new_language))
if "https://oapnfhnvisujhrfdvklm.supabase.co" in path.read_text():
    raise SystemExit("Production API reference remains")
print("Recovered frontend wired to same-origin /api.")
print("Editor defaults to a language supported by the exercise.")
