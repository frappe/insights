#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from fnmatch import fnmatch
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import NoDataError

APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APP = APP_ROOT.name
LEGACY_GLOBS_FILE = Path(__file__).with_name("legacy_v2_python_globs.txt")
COVERAGE_CONFIG_FILE = APP_ROOT / ".coveragerc"
SKIP_DIRS = {"node_modules", "locals", "public", "__pycache__"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Insights backend tests while excluding legacy v2 code from discovery and coverage."
    )
    parser.add_argument("--site", help="Site to run tests against")
    parser.add_argument("--app", default=DEFAULT_APP, help="App to run tests for")
    parser.add_argument(
        "--coverage-file",
        default="sites/coverage.xml",
        help="Coverage XML output path, relative to the current working directory",
    )
    parser.add_argument(
        "--legacy-globs-file",
        default=str(LEGACY_GLOBS_FILE),
        help="Path to the legacy v2 path glob list",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Print the included and excluded test modules without running tests",
    )
    return parser.parse_args()


def dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def load_globs(path: Path) -> list[str]:
    patterns: list[str] = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return patterns


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def discover_test_modules(app_root: Path, legacy_globs: list[str]) -> tuple[list[str], list[str]]:
    modules: list[str] = []
    excluded: list[str] = []

    for file_path in sorted(app_root.rglob("test_*.py")):
        rel_path = file_path.relative_to(app_root)
        rel_path_str = rel_path.as_posix()

        if file_path.name == "test_runner.py":
            continue

        if any(part.startswith(".") for part in rel_path.parts):
            continue

        if any(skip_dir in rel_path.parts for skip_dir in SKIP_DIRS):
            continue

        if "doctype/doctype/boilerplate" in rel_path_str:
            continue

        module_name = ".".join(file_path.relative_to(app_root).with_suffix("").parts)
        if matches_any(rel_path_str, legacy_globs):
            excluded.append(module_name)
            continue

        modules.append(module_name)

    return modules, excluded


def load_base_omit_patterns(config_file: Path) -> list[str]:
    if not config_file.exists():
        return []

    coverage = Coverage(config_file=str(config_file))
    return dedupe(list(coverage.config.run_omit) + list(coverage.config.report_omit))


def build_coverage_omit_patterns(base_patterns: list[str], legacy_globs: list[str]) -> list[str]:
    from frappe.coverage import STANDARD_EXCLUSIONS

    legacy_patterns = [f"*/{pattern}" for pattern in legacy_globs]
    return dedupe(STANDARD_EXCLUSIONS + base_patterns + legacy_patterns)


def run_tests(site: str, app: str, modules: list[str], coverage_file: Path, omit_patterns: list[str]) -> None:
    import frappe
    from frappe.commands.testing import main as run_tests_main

    bench_root = Path.cwd()
    coverage_file = coverage_file if coverage_file.is_absolute() else bench_root / coverage_file
    sites_dir = bench_root / "sites"
    original_cwd = Path.cwd()
    source_root = APP_ROOT / app
    coverage = Coverage(
        source=[str(source_root)],
        omit=omit_patterns,
    )

    coverage_file.parent.mkdir(parents=True, exist_ok=True)
    coverage_started = False

    try:
        os.chdir(sites_dir)
        frappe.init(site)
        coverage.start()
        coverage_started = True
        run_tests_main(site=site, app=app, module=modules)
    finally:
        if coverage_started:
            coverage.stop()
            coverage.save()
            try:
                coverage.xml_report(outfile=str(coverage_file))
            except NoDataError:
                print("No coverage data collected")
        frappe.destroy()
        os.chdir(original_cwd)
        print(f"Saved Coverage: {coverage_file}")


def main() -> None:
    args = parse_args()
    legacy_globs = load_globs(Path(args.legacy_globs_file))
    modules, excluded_modules = discover_test_modules(APP_ROOT, legacy_globs)

    print(f"Included test modules: {len(modules)}")
    print(f"Excluded legacy test modules: {len(excluded_modules)}")

    if excluded_modules:
        for module_name in excluded_modules:
            print(f"- {module_name}")

    if args.list_only:
        return

    if not args.site:
        raise SystemExit("--site is required unless --list-only is used")

    if not modules:
        raise SystemExit("No backend test modules remain after applying the legacy v2 exclusions")

    omit_patterns = build_coverage_omit_patterns(
        load_base_omit_patterns(COVERAGE_CONFIG_FILE),
        legacy_globs,
    )
    run_tests(args.site, args.app, modules, Path(args.coverage_file), omit_patterns)


if __name__ == "__main__":
    main()
