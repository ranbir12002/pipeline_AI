import os
import re
import base64
import logging
import requests
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Repo Analyzer API",
    description="Securely analyze GitHub repository contents for CI/CD and dependency files.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ======================
# MODEL DEFINITIONS
# ======================
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
        min_length=40,
        example="ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        description="GitHub Personal Access Token with **read-only repo access**."
    )
    max_lines: int = Field(
        300,
        ge=10,
        le=100000,
        example=300,
        description="Max lines to retain for large lockfiles."
    )

    @validator("repo_url")
    def validate_github_url(cls, v):
        v = v.strip()
        if not v.startswith("https://github.com/"):
            raise ValueError("URL must be a valid GitHub HTTPS URL.")
        pattern = r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$"
        if not re.match(pattern, v):
            raise ValueError("Invalid GitHub repository URL format.")
        return v

class TechItem(BaseModel):
    name: str
    version: str

class ProjectAnalysisInput(BaseModel):
    repo_url: str
    branch: str
    tech_stack: List[TechItem]
    project_type: str
    runtime_versions: List[TechItem]

class PipelineStepInput(BaseModel):
    id: str
    name: str
    description: str
    category: str
    default_command: str
    optional: bool

class PipelineGenerationRequest(BaseModel):
    project_analysis: ProjectAnalysisInput
    ci_pipeline_steps: List[PipelineStepInput] = Field(
        ...,
        description="User-selected steps for the pipeline"
    )

class GeneratedPipeline(BaseModel):
    github_actions_yaml: str = Field(
        ...,
        description="Valid GitHub Actions workflow YAML (ready to save as .github/workflows/ci.yml)"
    )
    manual_instructions: str = Field(
        ...,
        description="Plain-text instructions for manual setup (secrets, permissions, etc.)"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Optional improvements or notes"
    )

# ======================
# HELPER FUNCTIONS
# ======================
def parse_owner_repo(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL."""
    parts = url.replace("https://github.com/", "").rstrip(".git").split("/")
    return parts[0], parts[1]

def extract_json_from_llm_output(text: str) -> dict:
    """Extract JSON from LLM output with Markdown code block handling."""
    json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    json_str = json_match.group(1) if json_match else text.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM JSON output: {e}")

# ======================
# ENDPOINTS
# ======================
@app.get('/')
def read_root():
    return {"status": "200 OK", "message": "Welcome to Pipeline AI Backend Service"}

@app.post(
    "/analyze",
    response_model=dict,
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
    api_base = "https://api.github.com"

    # Fetch repository tree
    tree_url = f"{api_base}/repos/{owner}/{repo}/git/trees/{request.branch}?recursive=1"
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

    # Process relevant files
    tree_data = tree_resp.json()
    file_paths = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]
    
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
    
    LARGE_FILE_SUFFIXES = (
        ".lock", "package-lock.json", "yarn.lock", 
        "pnpm-lock.yaml", "poetry.lock"
    )

    relevant_paths = set()
    for path in file_paths:
        lower_path = path.lower()
        if lower_path in RELEVANT_FILES["common"]:
            relevant_paths.add(path)
            continue
            
        if lower_path.startswith(".github/workflows/") and lower_path.endswith((".yml", ".yaml")):
            relevant_paths.add(path)
            continue
            
        for lang_files in RELEVANT_FILES.values():
            if lower_path in lang_files or any(lower_path.endswith(f"/{f}") for f in lang_files):
                relevant_paths.add(path)
                break

    # Fetch and filter file contents
    results = {}
    for filepath in relevant_paths:
        content_url = f"{api_base}/repos/{owner}/{repo}/contents/{filepath}?ref={request.branch}"
        try:
            content_resp = requests.get(content_url, headers=headers, timeout=10)
            if content_resp.status_code != 200:
                continue
        except requests.RequestException:
            continue

        data = content_resp.json()
        if data.get("type") != "file":
            continue

        try:
            content = base64.b64decode(data["content"]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue

        # Filter large lockfiles
        if any(filepath.lower().endswith(suffix) for suffix in LARGE_FILE_SUFFIXES):
            lines = content.splitlines()
            important_lines = [
                line for line in lines
                if "version" in line.lower() or "@" in line or "resolved" in line.lower()
            ]
            content = "\n".join(important_lines[:request.max_lines] or lines[:request.max_lines])

        results[filepath] = content

    # Build snapshot from all relevant files
    snapshot = "\n\n".join(
        f"File: {path}\n{content}" for path, content in results.items()
    ) or "No relevant files found in repository"

    # Prepare LLM prompt
    repo_details = f"Repository: {request.repo_url}\nBranch: {request.branch}"
    
    prompt = [
        SystemMessage(content=(
            "You are an expert DevOps engineer specializing in CI pipeline generation. "
            "Output ONLY a valid JSON object with NO extra text, markdown, or explanations. "
            "The output will be parsed programmatically for a drag-and-drop pipeline builder."
        )),
        HumanMessage(content=(
            f"Analyze the repository snapshot and meta\n\n"
            f"--- REPOSITORY SNAPSHOT ---\n{snapshot}\n\n"
            f"--- REPO METADATA ---\n{repo_details}\n\n"
            "Generate a JSON object with EXACTLY these top-level keys:\n"
            "1. `project_analysis`: Object with repo_url, branch, tech_stack (with versions), "
            "project_type, runtime_versions\n"
            "2. `ci_pipeline_steps`: Array of step objects for pipeline builder\n\n"
            "RULES FOR `ci_pipeline_steps`:\n"
            "- Each step MUST have: id (snake_case), name, description, category, default_command\n"
            "- Commands must be executable in shell (e.g., 'npm ci')\n"
            "- NO markdown, NO code blocks, NO extra fields\n"
            "- Steps should be in logical order\n\n"
            "IMPORTANT: Output ONLY the JSON object. NO prefixes, NO suffixes, NO ```json blocks."
        ))
    ]

    # Call LLM
    try:
        llm = ChatGoogleGenerativeAI(
            api_key="AIzaSyDjSMkvmTaesnYoeXQPs5T79iR2ba4mX9Q",
            model="gemini-2.5-pro",
            temperature=0.1
        )
        response = llm.invoke(prompt)
        return extract_json_from_llm_output(response.content)
    except Exception as e:
        logger.error(f"LLM processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze repository")

@app.post(
    "/generate-pipeline",
    response_model=GeneratedPipeline,
    summary="Generate GitHub Actions pipeline",
    description="Convert selected CI pipeline steps into a production-ready GitHub Actions workflow."
)
def generate_pipeline(request: PipelineGenerationRequest):
    # Build context string
    context = (
        "Project Analysis:\n"
        f"- Repo: {request.project_analysis.repo_url}\n"
        f"- Branch: {request.project_analysis.branch}\n"
        f"- Project Type: {request.project_analysis.project_type}\n"
        f"- Tech Stack: {', '.join([f'{t.name} ({t.version})' for t in request.project_analysis.tech_stack])}\n"
        f"- Runtime: {', '.join([f'{r.name} {r.version}' for r in request.project_analysis.runtime_versions])}\n\n"
        "Selected CI Steps:\n"
    )
    
    for step in request.ci_pipeline_steps:
        context += (
            f"- [{step.category}] {step.name}: {step.description}\n"
            f"  Command: `{step.default_command}`\n"
        )

    # Prepare LLM prompt
    prompt = [
        SystemMessage(content=(
            "You are a GitHub Actions expert. Generate a production-ready CI workflow YAML "
            "and clear manual setup instructions. Output ONLY a JSON object with keys: "
            "'github_actions_yaml', 'manual_instructions', and optionally 'suggestions'. "
            "NO markdown, NO code blocks, NO extra text."
        )),
        HumanMessage(content=(
            f"Generate a GitHub Actions pipeline based on this context:\n\n{context}\n\n"
            "Requirements:\n"
            "1. Workflow name: 'CI'\n"
            "2. Trigger: on push to the specified branch\n"
            "3. Use ubuntu-latest runner\n"
            "4. Each step must use the provided 'default_command'\n"
            "5. For 'Setup Node.js', use actions/setup-node@v4 with correct version\n"
            "6. For 'Checkout Code', use actions/checkout@v4\n"
            "7. Install dependencies with 'npm ci'\n"
            "8. If linting/test steps are included, run them\n"
            "9. Build step must run 'npm run build'\n\n"
            "Manual Instructions should include:\n"
            "- Required secrets (e.g., if deploying)\n"
            "- Repository permissions (e.g., Actions → General → 'Read and write permissions')\n"
            "- Any file changes needed (e.g., add .github/workflows/ci.yml)\n\n"
            "Suggestions may include:\n"
            "- Caching node_modules\n"
            "- Adding test coverage\n"
            "- Enabling dependency updates\n\n"
            "OUTPUT FORMAT (STRICT JSON):\n"
            "{\n"
            "  \"github_actions_yaml\": \"name: CI\\non:\\n  push:\\n    branches: [master]\\n...\",\n"
            "  \"manual_instructions\": \"1. Go to Settings > Actions > General...\",\n"
            "  \"suggestions\": [\"Add caching for node_modules\", \"Consider adding Playwright tests\"]\n"
            "}\n\n"
            "IMPORTANT: Output ONLY the JSON. No prefixes, no suffixes, no ```json."
        ))
    ]

    # Call LLM
    try:
        llm = ChatGoogleGenerativeAI(
            api_key="AIzaSyDjSMkvmTaesnYoeXQPs5T79iR2ba4mX9Q",
            model="gemini-2.5-pro",
            temperature=0.1
        )
        response = llm.invoke(prompt)
        
        # Handle empty response
        if not response.content.strip():
            raise ValueError("LLM returned empty response")
            
        # Use the helper function to extract JSON (handles Markdown blocks)
        parsed = extract_json_from_llm_output(response.content)
        return GeneratedPipeline(
            github_actions_yaml=parsed["github_actions_yaml"],
            manual_instructions=parsed["manual_instructions"],
            suggestions=parsed.get("suggestions", [])
        )
    except ValueError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        logger.error(f"Raw response: {response.content}")
        raise HTTPException(status_code=500, detail="Failed to parse pipeline generation response")
    except Exception as e:
        logger.error(f"Pipeline generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate pipeline")