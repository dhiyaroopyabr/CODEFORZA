"""
executor.py — Sandboxed code execution engine for the online judge.

Supported languages : Python 3, C++ (g++), C (gcc), Java
Security model      : subprocess with hard timeout + temp directory isolation
                      (for production, replace with Docker containers)

⚠️  WARNING: This executor runs arbitrary code on the host machine.
    Never expose /api/judge/run to the public internet without Docker sandboxing.
    Suitable for a controlled college LAN or localhost development only.
"""

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ── Language configuration ────────────────────────────────────────────────────

SUPPORTED_LANGUAGES = {"python", "cpp", "c", "java"}

# Java requires the public class to match the filename, so we always name it Main
_LANG_CFG = {
    "python": {
        "ext": ".py",
        "compile": None,
        "run": ["python3", "{source}"],
    },
    "cpp": {
        "ext": ".cpp",
        "compile": ["g++", "-O2", "-std=c++17", "-o", "{binary}", "{source}"],
        "run": ["{binary}"],
    },
    "c": {
        "ext": ".c",
        "compile": ["gcc", "-O2", "-o", "{binary}", "{source}"],
        "run": ["{binary}"],
    },
    "java": {
        "ext": ".java",
        "compile": ["javac", "{source}"],
        "run": ["java", "-cp", "{dir}", "Main"],
    },
}

# Output / error truncation limits (bytes)
_MAX_STDOUT = 8192
_MAX_STDERR = 2048
_COMPILE_TIMEOUT = 30  # seconds


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ExecutionResult:
    status: str           # OK | TLE | RE | CE
    stdout: str
    stderr: str
    execution_time: float # wall-clock seconds


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(template: List[str], **kwargs: str) -> List[str]:
    """Substitute {placeholders} in a command token list."""
    return [t.format(**kwargs) for t in template]


# ── Core execution ────────────────────────────────────────────────────────────

def execute_code(
    language: str,
    code: str,
    stdin_data: str = "",
    time_limit: float = 5.0,
) -> ExecutionResult:
    """
    Write code to a temp dir, compile if needed, then execute.

    Returns an ExecutionResult regardless of outcome.
    The temp directory is always cleaned up.
    """
    if language not in SUPPORTED_LANGUAGES:
        return ExecutionResult(
            status="CE",
            stdout="",
            stderr=f"Unsupported language '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}",
            execution_time=0.0,
        )

    cfg = _LANG_CFG[language]
    tmpdir = tempfile.mkdtemp(prefix="judge_")

    try:
        # ── 1. Write source file ─────────────────────────────────────────────
        src_name = "Main" if language == "java" else "solution"
        source_path = os.path.join(tmpdir, src_name + cfg["ext"])
        binary_path = os.path.join(tmpdir, "solution")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(code)

        # ── 2. Compile (if needed) ───────────────────────────────────────────
        if cfg["compile"]:
            compile_cmd = _fmt(
                cfg["compile"],
                source=source_path,
                binary=binary_path,
                dir=tmpdir,
            )
            try:
                cp = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=_COMPILE_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult("CE", "", "Compilation timed out.", 0.0)

            if cp.returncode != 0:
                return ExecutionResult(
                    status="CE",
                    stdout="",
                    stderr=cp.stderr[:_MAX_STDERR],
                    execution_time=0.0,
                )

        # ── 3. Execute ───────────────────────────────────────────────────────
        run_cmd = _fmt(
            cfg["run"],
            source=source_path,
            binary=binary_path,
            dir=tmpdir,
        )

        t0 = time.perf_counter()
        try:
            rp = subprocess.run(
                run_cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=time_limit,
            )
            elapsed = time.perf_counter() - t0
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status="TLE",
                stdout="",
                stderr=f"Time limit exceeded ({time_limit:.1f}s)",
                execution_time=time_limit,
            )

        if rp.returncode != 0:
            return ExecutionResult(
                status="RE",
                stdout=rp.stdout[:_MAX_STDOUT],
                stderr=rp.stderr[:_MAX_STDERR],
                execution_time=elapsed,
            )

        return ExecutionResult(
            status="OK",
            stdout=rp.stdout[:_MAX_STDOUT],
            stderr=rp.stderr[:_MAX_STDERR],
            execution_time=elapsed,
        )

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Judge (run against test cases) ────────────────────────────────────────────

def judge_submission(
    language: str,
    code: str,
    test_cases: List[Tuple[str, str]],  # [(input, expected_output), ...]
    time_limit: float = 2.0,
) -> dict:
    """
    Run code against every test case and return the overall verdict.

    Fail-fast: returns immediately on the first non-AC result.
    Output comparison strips trailing whitespace per Codeforces convention.

    Returns:
        {
            status: "AC" | "WA" | "TLE" | "MLE" | "RE" | "CE",
            execution_time: float,
            stderr: str,
            test_results: [{"test_case": int, "status": str, "time": float}]
        }
    """
    if not test_cases:
        # No test cases — just compile/run the code as a sanity check
        result = execute_code(language, code, "", time_limit)
        return {
            "status": result.status if result.status != "OK" else "AC",
            "execution_time": result.execution_time,
            "stderr": result.stderr,
            "test_results": [],
        }

    overall_status = "AC"
    max_time = 0.0
    test_results = []

    for i, (inp, expected) in enumerate(test_cases, start=1):
        result = execute_code(language, code, inp, time_limit)
        max_time = max(max_time, result.execution_time)

        if result.status == "CE":
            return {
                "status": "CE",
                "execution_time": 0.0,
                "stderr": result.stderr,
                "test_results": [],
            }

        if result.status != "OK":
            test_results.append({"test_case": i, "status": result.status, "time": result.execution_time})
            overall_status = result.status
            break

        # Strip trailing whitespace and normalise line endings (CF convention)
        actual = result.stdout.strip().replace("\r\n", "\n")
        expected_clean = expected.strip().replace("\r\n", "\n")

        if actual != expected_clean:
            test_results.append({"test_case": i, "status": "WA", "time": result.execution_time})
            overall_status = "WA"
            break

        test_results.append({"test_case": i, "status": "AC", "time": result.execution_time})

    return {
        "status": overall_status,
        "execution_time": max_time,
        "stderr": "",
        "test_results": test_results,
    }
