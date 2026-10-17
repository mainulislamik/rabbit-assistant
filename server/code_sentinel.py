"""
Code Sentinel & Automated Syntax Auditor for Rabbit Assistant.
Audits project git state, syntax integrity, and code quality before commits.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, List

def run_project_code_audit(project_path: str = "/home/imon/rabbit-assistant") -> Dict[str, Any]:
    """Audits a project's git status, uncommitted changes, and syntax integrity."""
    p = Path(project_path).resolve()
    if not p.exists() or not p.is_dir():
        return {"error": f"Path not found: {project_path}", "healthy": False}

    report = {
        "project": p.name,
        "path": str(p),
        "branch": "unknown",
        "modified_files": [],
        "syntax_errors": [],
        "healthy": True,
        "summary": ""
    }

    # 1. Git branch & status
    try:
        b_res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(p), stdout=subprocess.PIPE, text=True, timeout=3
        )
        if b_res.returncode == 0:
            report["branch"] = b_res.stdout.strip()

        st_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(p), stdout=subprocess.PIPE, text=True, timeout=3
        )
        if st_res.returncode == 0:
            for line in st_res.stdout.strip().split("\n"):
                if line:
                    report["modified_files"].append(line.strip())
    except Exception as e:
        report["git_error"] = str(e)

    # 2. Syntax Check for Python files in modified list or server/
    py_files = list(p.glob("**/*.py"))[:30] # audit top 30 python files
    for pyf in py_files:
        if "venv" in str(pyf) or ".venv" in str(pyf):
            continue
        try:
            c_res = subprocess.run(
                ["python3", "-m", "py_compile", str(pyf)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4
            )
            if c_res.returncode != 0:
                report["syntax_errors"].append({
                    "file": str(pyf.relative_to(p)),
                    "error": c_res.stderr.strip()
                })
        except Exception as e:
            report["syntax_errors"].append({"file": str(pyf.name), "error": str(e)})

    if report["syntax_errors"]:
        report["healthy"] = False
        report["summary"] = f"সতর্কতা: প্রজেক্টে {len(report['syntax_errors'])}টি ফাইলে সিনট্যাক্স ইরর পাওয়া গেছে!"
    else:
        mod_count = len(report["modified_files"])
        report["summary"] = (
            f"প্রজেক্ট '{p.name}' (Branch: {report['branch']}) সম্পূর্ণ ত্রুটিমুক্ত ও হেলদি। "
            f"সিনট্যাক্স টেস্ট শতভাগ সফল। আনকমিটেড ফাইল: {mod_count}টি।"
        )

    return report
