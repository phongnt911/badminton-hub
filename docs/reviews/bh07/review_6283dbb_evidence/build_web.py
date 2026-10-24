import json
import subprocess
from pathlib import Path

ROOT = Path(r"C:\Users\POTA\Documents\GitHub\badminton-hub")
OUT = Path(r"C:\Users\POTA\AppData\Local\Temp\bh07-v1-review")
runtime = json.loads((OUT / "private/runtime.json").read_text(encoding="utf-8"))
log = (OUT / "web_build.log").open("w", encoding="utf-8")
cmd = [
    r"C:\src\flutter\bin\flutter.bat", "build", "web", "--no-pub", "--no-web-resources-cdn",
    "--dart-define=APP_ENV=test",
    f"--dart-define=SUPABASE_URL={runtime['api_url']}",
    f"--dart-define=SUPABASE_ANON_KEY={runtime['anon']}",
]
r = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", stdout=log, stderr=subprocess.STDOUT)
log.close()
(OUT / "web_build_exit.txt").write_text(str(r.returncode) + "\n", encoding="utf-8")
print("build exit", r.returncode)
if r.returncode:
    print((OUT / "web_build.log").read_text(encoding="utf-8", errors="replace")[-4000:])
