"""Code security scanner for expert-uploaded Python scripts and requirements."""
import ast
import hashlib
import logging
import re
import subprocess
import tempfile

logger = logging.getLogger("neurohub.scanner")

BANNED_IMPORTS = frozenset([
    "subprocess", "socket", "ctypes", "cffi", "multiprocessing",
    "pickle", "marshal", "shelve", "pty", "tty", "termios",
    "ftplib", "telnetlib", "imaplib", "smtplib", "poplib",
    "xmlrpc", "http.server", "socketserver",
])

BANNED_BUILTINS = frozenset([
    "exec", "eval", "compile", "__import__", "open",
    "input", "breakpoint",
])

ALLOWED_PACKAGES = frozenset([
    "numpy", "scipy", "pandas", "scikit-learn", "sklearn",
    "torch", "torchvision", "torchaudio", "timm",
    "tensorflow", "keras", "tf",
    "onnxruntime", "onnx",
    "pydicom", "nibabel", "SimpleITK", "medpy", "dicom2nifti",
    "highdicom", "pynetdicom",
    "opencv-python", "cv2", "Pillow", "PIL", "albumentations",
    "monai", "antspyx",
    "mne", "antropy", "fooof", "yasa",
    "tqdm", "pyyaml", "yaml", "h5py", "matplotlib",
    "seaborn", "plotly", "joblib", "psutil",
    "neurohub-sdk", "neurohub_sdk",
    # standard lib safe ones
    "os.path", "pathlib", "json", "csv", "math", "random",
    "datetime", "collections", "itertools", "functools",
    "typing", "dataclasses", "enum", "abc", "copy",
    "hashlib", "base64", "struct", "io", "gzip", "zipfile",
    "logging", "warnings", "time", "traceback",
    "unittest", "pytest",
])


def check_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def scan_python_ast(source_code: str) -> list[dict]:
    """AST-based scan for banned imports and builtins."""
    findings = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return [{"rule": "SYNTAX_ERROR", "severity": "HIGH", "message": str(e), "line": e.lineno}]

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in BANNED_IMPORTS:
                        findings.append({
                            "rule": "BANNED_IMPORT",
                            "severity": "HIGH",
                            "message": f"Banned import: {alias.name}",
                            "line": node.lineno,
                        })
            elif isinstance(node, ast.ImportFrom) and node.module:
                module = node.module.split(".")[0]
                if module in BANNED_IMPORTS:
                    findings.append({
                        "rule": "BANNED_IMPORT",
                        "severity": "HIGH",
                        "message": f"Banned import from: {node.module}",
                        "line": node.lineno,
                    })

        # Check banned builtins
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_BUILTINS:
                findings.append({
                    "rule": "BANNED_BUILTIN",
                    "severity": "CRITICAL",
                    "message": f"Banned builtin call: {node.func.id}()",
                    "line": node.lineno,
                })
            # Check os.system, os.popen etc
            if isinstance(node.func, ast.Attribute):
                full = f"{getattr(node.func.value, 'id', '')}.{node.func.attr}"
                if full in {"os.system", "os.popen", "os.execv", "os.execvp", "os.fork",
                            "os.spawn", "shutil.rmtree"}:
                    findings.append({
                        "rule": "DANGEROUS_CALL",
                        "severity": "CRITICAL",
                        "message": f"Dangerous call: {full}()",
                        "line": node.lineno,
                    })

    return findings


def scan_requirements(requirements_txt: str) -> list[dict]:
    """Check requirements.txt against allowed package list."""
    findings = []
    for line in requirements_txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Extract package name (remove version specifiers)
        pkg_name = re.split(r"[>=<!;\[]", line)[0].strip().lower().replace("_", "-")
        # Check against allowed list (normalize)
        allowed_normalized = {p.lower().replace("_", "-") for p in ALLOWED_PACKAGES}
        if pkg_name and pkg_name not in allowed_normalized:
            findings.append({
                "rule": "UNLISTED_PACKAGE",
                "severity": "MEDIUM",
                "message": f"Package not in allowlist: {pkg_name}",
                "package": pkg_name,
            })
    return findings


def run_bandit(source_code: str) -> list[dict]:
    """Run bandit static analysis. Returns findings list."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(source_code)
            tmp_path = f.name

        result = subprocess.run(
            ["bandit", "-f", "json", "-q", tmp_path],
            capture_output=True, text=True, timeout=30
        )
        import json
        if result.stdout:
            data = json.loads(result.stdout)
            return [
                {
                    "rule": r.get("test_id"),
                    "severity": r.get("issue_severity", "LOW").upper(),
                    "message": r.get("issue_text"),
                    "line": r.get("line_number"),
                    "confidence": r.get("issue_confidence"),
                }
                for r in data.get("results", [])
            ]
    except FileNotFoundError:
        logger.warning("bandit not installed, skipping bandit scan")
    except Exception as e:
        logger.error("bandit scan failed: %s", e)
    return []


def determine_overall_status(all_findings: list[dict]) -> tuple[str, str | None]:
    """Returns (status, max_severity). status: PASS | WARN | FAIL"""
    if not all_findings:
        return "PASS", None
    severities = [f.get("severity", "LOW") for f in all_findings]
    if "CRITICAL" in severities or "HIGH" in severities:
        return "FAIL", "HIGH" if "HIGH" in severities else "CRITICAL"
    if "MEDIUM" in severities:
        return "WARN", "MEDIUM"
    return "WARN", "LOW"
