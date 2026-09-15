import json
from pathlib import Path


def test_package_include_ships_app_modules() -> None:
    rules = json.loads(Path("deploy/package-include.json").read_text(encoding="utf-8"))
    for required in ("ovadue", "pages", "app.py", "scripts", "deploy", "Product Info"):
        assert required in rules["includePaths"]
    assert "data\\backups" in rules["neverPackage"]
    assert "data\\backups\\**" in rules["preserveOnUpgrade"]


def test_backup_script_exists() -> None:
    assert Path("scripts/OvaDue-Backup.ps1").is_file()
    assert Path("scripts/probe_sqlite.py").is_file()
