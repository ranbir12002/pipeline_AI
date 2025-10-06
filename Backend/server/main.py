from fastapi import FastAPI
import requests
import os
import base64
from typing import Dict
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional
import re
import base64
import requests
import logging
import os







# Optional: enable structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Repo Analyzer API",
    description="Securely analyze GitHub repository contents for CI/CD and dependency files.",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)
@app.get('/')
def read_root():
    return {"status": "200 OK", "message": "Welcome to Pipeline AI Backend Service"}



# --- Input Model ---
class RepoAnalysisRequest(BaseModel):
    repo_url: str = Field(
        ...,
        example="https://github.com/psf/requests",
        description="Full GitHub repository URL (https only)."
    )
    branch: str = Field(
        "main",
        min_length=1,
        max_length=100,
        example="main",
        description="Branch, tag, or commit SHA."
    )
    github_pat: str = Field(
        ...,
        min_length=40,  # GitHub PATs are at least 40 chars
        example="ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        description="GitHub Personal Access Token with **read-only repo access**."
    )
    max_lines: int = Field(
        300,
        ge=10,
        le=1000,
        example=300,
        description="Max lines to retain for large lockfiles."
    )

    @validator("repo_url")
    def validate_github_url(cls, v):
        v = v.strip()
        if not v.startswith("https://github.com/"):
            raise ValueError("URL must be a valid GitHub HTTPS URL.")
        # Match: https://github.com/owner/repo[.git]
        pattern = r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$"
        if not re.match(pattern, v):
            raise ValueError("Invalid GitHub repository URL format.")
        return v

# --- Helper: Parse owner/repo ---
def parse_owner_repo(url: str) -> tuple[str, str]:
    # Safe after validation
    parts = url.replace("https://github.com/", "").rstrip(".git").split("/")
    return parts[0], parts[1]

# --- Constants ---
RELEVANT_FILES = {
    "common": {
        "dockerfile", ".docker/dockerfile", "docker-compose.yml",
        "jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml",
        ".circleci/config.yml", "readme.md"
    },
    "node": {"package.json", "yarn.lock", "pnpm-lock.yaml", "package-lock.json"},
    "python": {"requirements.txt", "pipfile", "pipfile.lock", "pyproject.toml", "poetry.lock"},
    "java": {"pom.xml", "build.gradle", "settings.gradle", "gradlew", "gradlew.bat"}
}

LARGE_FILE_SUFFIXES = (".lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock")

# --- Main Endpoint ---
@app.post(
    "/analyze",
    response_model=Dict[str, str],
    summary="Analyze GitHub repository contents",
    description="""
    Fetches and filters relevant CI/CD and dependency files from a GitHub repository.
    - Only files matching predefined patterns are returned.
    - Large lockfiles are filtered to retain version-relevant lines.
    - The provided PAT is used only for this request and never stored.
    """
)
def analyze_repo(request: RepoAnalysisRequest):
    try:
        owner, repo = parse_owner_repo(request.repo_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid repo URL: {str(e)}")

    headers = {
        "Authorization": f"token {request.github_pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "RepoAnalyzer/1.0"
    }

    API_BASE = "https://api.github.com"

    # Fetch repo tree
    tree_url = f"{API_BASE}/repos/{owner}/{repo}/git/trees/{request.branch}?recursive=1"
    try:
        tree_resp = requests.get(tree_url, headers=headers, timeout=10)
    except requests.RequestException as e:
        logger.error(f"Tree fetch failed for {owner}/{repo}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reach GitHub API")

    if tree_resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or insufficient GitHub token")
    elif tree_resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Repository or branch not found")
    elif tree_resp.status_code != 200:
        logger.error(f"GitHub API error ({tree_resp.status_code}): {tree_resp.text}")
        raise HTTPException(status_code=502, detail="GitHub API returned an error")

    tree_data = tree_resp.json()
    file_paths = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

    # Normalize and collect relevant files
    relevant_paths = set()
    for path in file_paths:
        lower_path = path.lower()
        # Common files
        if lower_path in RELEVANT_FILES["common"]:
            relevant_paths.add(path)
        # GitHub Actions
        if lower_path.startswith(".github/workflows/") and lower_path.endswith((".yml", ".yaml")):
            relevant_paths.add(path)
        # Language-specific
        for lang_files in RELEVANT_FILES.values():
            if lower_path in lang_files or any(lower_path.endswith(f"/{f}") for f in lang_files):
                relevant_paths.add(path)

    # Fetch and filter file contents
    results: Dict[str, str] = {}
    for filepath in relevant_paths:
        content_url = f"{API_BASE}/repos/{owner}/{repo}/contents/{filepath}?ref={request.branch}"
        try:
            content_resp = requests.get(content_url, headers=headers, timeout=10)
        except requests.RequestException:
            continue  # skip on network error

        if content_resp.status_code != 200:
            continue

        data = content_resp.json()
        if data.get("type") != "file":
            continue

        try:
            content = base64.b64decode(data["content"]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue

        # Smart filtering for large lockfiles
        lower_fp = filepath.lower()
        if any(lower_fp.endswith(suffix) for suffix in LARGE_FILE_SUFFIXES):
            lines = content.splitlines()
            # Prioritize lines with versions or package identifiers
            important_lines = [
                line for line in lines
                if "version" in line.lower() or "@" in line or "resolved" in line.lower()
            ]
            # Use important lines if available, else fallback to head
            selected_lines = important_lines if important_lines else lines
            content = "\n".join(selected_lines[:request.max_lines])

        results[filepath] = content

    return results