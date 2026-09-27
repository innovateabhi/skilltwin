import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.trainee import Trainee
from app.models.trainee_competency import TraineeCompetency
from app.models.competency import Competency
from app.models.skill import Skill
from ai.ollama_service import generate_ai_response


router = APIRouter(
    prefix="/api/ai-resume",
    tags=["AI Resume"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class ResumeGenerateRequest(BaseModel):
    target_role: str = Field(..., min_length=2, max_length=150)
    job_description: str | None = None

    email: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    selected_skills: list[str] = Field(default_factory=list)

    summary: str | None = None
    experience: str | None = None
    projects: str | None = None
    certifications: str | None = None


class ResumeImproveRequest(BaseModel):
    section: str = Field(..., min_length=2, max_length=50)
    content: str = Field(..., min_length=1)
    target_role: str | None = None
    job_description: str | None = None


class ATSAnalysisRequest(BaseModel):
    target_role: str = Field(..., min_length=2, max_length=150)
    job_description: str = Field(..., min_length=10)
    resume: dict


# ============================================================
# PROFILE
# ============================================================

def get_resume_profile(
    current_user: User,
    db: Session,
) -> dict:

    trainee = db.scalar(
        select(Trainee).where(
            Trainee.user_id == current_user.id
        )
    )

    if not trainee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainee profile not found.",
        )

    rows = db.execute(
        select(
            Skill.id,
            Skill.name,
            Competency.id,
            Competency.name,
            TraineeCompetency.current_score,
            TraineeCompetency.target_score,
        )
        .join(
            TraineeCompetency,
            TraineeCompetency.competency_id == Competency.id,
        )
        .join(
            Skill,
            Skill.id == Competency.skill_id,
        )
        .where(
            TraineeCompetency.trainee_id == trainee.id
        )
    ).all()

    skills_map: dict[int, dict] = {}
    competencies: list[dict] = []

    for row in rows:
        (
            skill_id,
            skill_name,
            competency_id,
            competency_name,
            current_score,
            target_score,
        ) = row

        if skill_id not in skills_map:
            skills_map[skill_id] = {
                "id": skill_id,
                "name": skill_name,
            }

        competencies.append(
            {
                "id": competency_id,
                "name": competency_name,
                "skill_name": skill_name,
                "current_score": current_score,
                "target_score": target_score,
            }
        )

    full_name = (
        f"{trainee.first_name or ''} "
        f"{trainee.last_name or ''}"
    ).strip()

    return {
        "id": trainee.id,
        "user_id": trainee.user_id,
        "full_name": full_name,
        "email": current_user.email,
        "phone": trainee.phone,
        "institution_name": trainee.institution_name,
        "education_level": trainee.education_level,
        "specialization": trainee.specialization,
        "target_role": trainee.target_role,
        "bio": trainee.bio,
        "profile_image": trainee.profile_image,
        "skills": list(skills_map.values()),
        "competencies": competencies,
    }


# ============================================================
# PROFILE ENDPOINT
# ============================================================

@router.get("/profile")
def get_profile_for_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_resume_profile(
        current_user=current_user,
        db=db,
    )

    return {
        "profile": profile,
    }


# ============================================================
# HELPERS
# ============================================================

def clean_ai_text(text: str) -> str:
    """
    Clean common Qwen formatting/reasoning leakage.
    """

    if not text:
        return ""

    text = text.strip()

    # Remove code fences.
    text = re.sub(
        r"```(?:text|markdown)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace("```", "").strip()

    # Remove common labels.
    text = re.sub(
        r"^(professional\s+summary|summary)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove obvious reasoning prefixes.
    text = re.sub(
        r"^(final\s+answer|final)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def is_reasoning_leak(text: str) -> bool:
    """
    Qwen 3 can occasionally return its internal reasoning or
    repeat the prompt. Reject that output instead of showing it
    to the trainee.
    """

    if not text:
        return True

    lower = text.lower()

    suspicious_phrases = [
        "we are given:",
        "rules to follow:",
        "candidate provided",
        "what we have:",
        "we cannot invent:",
        "therefore the summary",
        "the summary must",
        "let's craft",
        "i need to",
        "i should",
        "analysis:",
        "final answer:",
        "job description mentions",
        "the candidate does not",
        "note that the candidate",
    ]

    if any(
        phrase in lower
        for phrase in suspicious_phrases
    ):
        return True

    if len(text) > 700:
        return True

    return False


def parse_lines(value: str | None) -> list[str]:
    if not value:
        return []

    return [
        line.strip()
        for line in value.splitlines()
        if line.strip()
    ]


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip()

    if not value:
        return None

    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"

    return value


def deterministic_summary(
    profile: dict,
    target_role: str,
    selected_skills: list[str],
    user_summary: str | None,
) -> str:

    if user_summary and user_summary.strip():
        return user_summary.strip()

    name = profile.get("full_name") or "Candidate"
    education = profile.get("education_level")
    specialization = profile.get("specialization")
    institution = profile.get("institution_name")

    education_text = " ".join(
        part
        for part in [
            education,
            specialization,
        ]
        if part
    )

    if not education_text:
        education_text = "undergraduate"

    skill_text = ", ".join(selected_skills[:5])

    if skill_text:
        return (
            f"{education_text} candidate at {institution or 'SkillTwin'} "
            f"targeting a {target_role} role, with verified skills in "
            f"{skill_text}. Interested in applying technical knowledge "
            f"to practical projects and continuing to develop "
            f"role-relevant capabilities."
        )

    return (
        f"{education_text} candidate at "
        f"{institution or 'SkillTwin'} targeting a "
        f"{target_role} role. Demonstrates a developing technical "
        f"foundation and a focus on building practical, "
        f"job-relevant capabilities."
    )


# ============================================================
# GENERATE RESUME
# ============================================================

@router.post("/generate")
async def generate_resume(
    request: ResumeGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    try:
        print("[AI Resume] Starting resume generation...")

        profile = get_resume_profile(
            current_user=current_user,
            db=db,
        )

        # ----------------------------------------------------
        # TRUSTED SKILLS ONLY
        # ----------------------------------------------------

        available_skill_names = [
            skill["name"]
            for skill in profile.get("skills", [])
            if skill.get("name")
        ]

        requested_skills = [
            str(skill).strip()
            for skill in request.selected_skills
            if str(skill).strip()
        ]

        # Only allow skills that actually exist in SkillTwin.
        selected_skills = [
            skill
            for skill in available_skill_names
            if skill in requested_skills
        ]

        # If the frontend doesn't send selected skills,
        # use all verified SkillTwin skills.
        if not selected_skills:
            selected_skills = available_skill_names

        # ----------------------------------------------------
        # CONTACT INFORMATION
        # ----------------------------------------------------

        email = (
            request.email.strip()
            if request.email
            else profile.get("email")
        )

        github_url = normalize_url(request.github_url)
        linkedin_url = normalize_url(request.linkedin_url)
        portfolio_url = normalize_url(request.portfolio_url)

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary = ""

        if request.summary and request.summary.strip():
            summary = request.summary.strip()

        else:
            system_prompt = """
You are SkillTwin's professional resume summary writer.

Write ONLY ONE professional resume summary.

Rules:
- Use only the candidate information supplied.
- Never invent experience.
- Never invent companies.
- Never invent certifications.
- Never invent achievements.
- Never invent metrics.
- Never claim a technology or skill that is not supplied.
- The target role is only used to understand the desired career direction.
- Job-description keywords may guide wording but must NOT be presented as candidate skills unless the candidate actually has them.
- Write 40 to 70 words.
- Use third person without the candidate's name.
- Do not use first person.
- Do not use headings.
- Do not use markdown.
- Do not explain anything.
- Return only the finished summary.
"""

            user_prompt = f"""
Candidate education:
{profile.get("education_level") or "Not provided"}

Specialization:
{profile.get("specialization") or "Not provided"}

Institution:
{profile.get("institution_name") or "Not provided"}

Verified SkillTwin skills:
{", ".join(selected_skills) or "None"}

Verified SkillTwin competencies:
{", ".join(
    c["name"]
    for c in profile.get("competencies", [])
    if c.get("name")
) or "None"}

Existing profile bio:
{profile.get("bio") or "Not provided"}

Target role:
{request.target_role}

Job description:
{request.job_description or "Not provided"}

Write the professional resume summary now.
"""

            print("[AI Resume] Requesting summary from Ollama...")

            response = await generate_ai_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            candidate_summary = clean_ai_text(
                response or ""
            )

            if (
                candidate_summary
                and not is_reasoning_leak(candidate_summary)
            ):
                summary = candidate_summary
                print("[AI Resume] AI summary accepted.")
            else:
                print(
                    "[AI Resume] AI summary rejected; "
                    "using deterministic summary."
                )

        if not summary:
            summary = deterministic_summary(
                profile=profile,
                target_role=request.target_role,
                selected_skills=selected_skills,
                user_summary=request.summary,
            )

        # ----------------------------------------------------
        # EXPERIENCE
        # ----------------------------------------------------

        experience_items = parse_lines(
            request.experience
        )

        experience = []

        for item in experience_items:
            experience.append(
                {
                    "title": item,
                    "company": "",
                    "description": [],
                }
            )

        # ----------------------------------------------------
        # PROJECTS
        # ----------------------------------------------------

        project_items = parse_lines(
            request.projects
        )

        projects = []

        for item in project_items:
            projects.append(
                {
                    "name": item,
                    "description": [],
                }
            )

        # ----------------------------------------------------
        # CERTIFICATIONS
        # ----------------------------------------------------

        certifications = parse_lines(
            request.certifications
        )

        # ----------------------------------------------------
        # EDUCATION FROM SKILLTWIN
        # ----------------------------------------------------

        education = []

        if any(
            [
                profile.get("education_level"),
                profile.get("specialization"),
                profile.get("institution_name"),
            ]
        ):
            education.append(
                {
                    "degree": profile.get(
                        "education_level"
                    ),
                    "institution": profile.get(
                        "institution_name"
                    ),
                    "specialization": profile.get(
                        "specialization"
                    ),
                }
            )

        # ----------------------------------------------------
        # FINAL RESUME
        # ----------------------------------------------------

        resume = {
            "contact": {
                "email": email,
                "phone": profile.get("phone"),
                "github_url": github_url,
                "linkedin_url": linkedin_url,
                "portfolio_url": portfolio_url,
            },
            "summary": summary,
            "skills": selected_skills,
            "education": education,
            "experience": experience,
            "projects": projects,
            "certifications": certifications,
        }

        print("[AI Resume] Resume generated successfully.")

        return {
            "profile": profile,
            "resume": resume,
            "target_role": request.target_role,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(
            "[AI Resume] Generation error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI resume service could not complete "
                "the request. Please try again."
            ),
        )


# ============================================================
# IMPROVE SECTION
# ============================================================

@router.post("/improve-section")
async def improve_resume_section(
    request: ResumeImproveRequest,
):

    system_prompt = """
You are SkillTwin AI Resume Editor.

Rewrite the supplied resume content professionally.

Rules:
- Preserve every factual claim.
- Never invent experience.
- Never invent companies.
- Never invent certifications.
- Never invent technologies.
- Never invent achievements.
- Never invent metrics.
- Never add information that is not present.
- Improve grammar and clarity.
- Make it concise and ATS-friendly.
- Return ONLY the rewritten text.
- Do not explain your reasoning.
"""

    user_prompt = f"""
Section:
{request.section}

Target role:
{request.target_role or "Not specified"}

Job description:
{request.job_description or "Not specified"}

Current content:
{request.content}

Rewrite it now.
"""

    try:
        response = await generate_ai_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        content = clean_ai_text(
            response or ""
        )

        if not content or is_reasoning_leak(content):
            raise ValueError(
                "AI returned unusable content."
            )

        return {
            "section": request.section,
            "content": content,
        }

    except Exception as exc:
        print(
            "[AI Resume] Section improvement error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI section improvement failed. "
                "Please try again."
            ),
        )


# ============================================================
# ATS ANALYSIS
# ============================================================

@router.post("/ats-analysis")
async def analyze_resume_ats(
    request: ATSAnalysisRequest,
):

    system_prompt = """
You are SkillTwin ATS Resume Analyzer.

Analyze the supplied resume against the supplied job description.

Return ONLY valid JSON.

Required format:

{
  "match_percentage": 0,
  "matched_keywords": [],
  "missing_keywords": [],
  "relevant_skills": [],
  "suggestions": []
}

Rules:
- match_percentage must be an integer from 0 to 100.
- Matched keywords must actually appear in the resume.
- Missing keywords must actually appear in the job description.
- Do not claim the candidate possesses a missing skill.
- Suggestions must be factual and based only on the supplied information.
"""

    resume_json = json.dumps(
        request.resume,
        ensure_ascii=False,
    )

    user_prompt = f"""
Target role:
{request.target_role}

Job description:
{request.job_description}

Resume:
{resume_json}

Return ONLY JSON.
"""

    try:
        response = await generate_ai_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        raw = (response or "").strip()

        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "AI did not return valid ATS JSON."
            )

        result = json.loads(
            raw[start:end + 1]
        )

        try:
            match_percentage = int(
                result.get(
                    "match_percentage",
                    0,
                )
            )
        except (
            ValueError,
            TypeError,
        ):
            match_percentage = 0

        match_percentage = max(
            0,
            min(100, match_percentage),
        )

        def normalize_list(value: Any):
            if not isinstance(value, list):
                return []

            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

        return {
            "available": True,
            "match_percentage": match_percentage,
            "matched_keywords": normalize_list(
                result.get("matched_keywords")
            ),
            "missing_keywords": normalize_list(
                result.get("missing_keywords")
            ),
            "relevant_skills": normalize_list(
                result.get("relevant_skills")
            ),
            "suggestions": normalize_list(
                result.get("suggestions")
            ),
        }

    except json.JSONDecodeError as exc:
        print(
            "[AI Resume] ATS JSON parsing error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI model returned an incomplete "
                "ATS analysis. Please try again."
            ),
        )

    except Exception as exc:
        print(
            "[AI Resume] ATS analysis error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "ATS analysis failed. Please try again."
            ),
        )