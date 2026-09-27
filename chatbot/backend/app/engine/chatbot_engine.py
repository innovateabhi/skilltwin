import json
import re
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"

def load_json(filename: str) -> dict[str, Any]:
    with (KNOWLEDGE_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)

KNOWLEDGE = {
    "skilltwin": load_json("skilltwin.json"),
    "services": load_json("services.json"),
    "solutions": load_json("solutions.json"),
    "pricing": load_json("pricing.json"),
    "portals": load_json("portals.json"),
    "faq": load_json("faq.json"),
}

def normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s?&.-]", " ", text)
    return re.sub(r"\s+", " ", text)

def tokens(text: str) -> set[str]:
    return {x for x in normalize(text).split() if len(x) > 2}

def bullets(items: list[str]) -> str:
    return "\n".join(f"• {item}" for item in items)

def best_faq_match(query: str):
    qtokens = tokens(query)
    best = None
    best_score = 0
    for item in KNOWLEDGE["faq"]["items"]:
        score = 0
        for keyword in item["keywords"]:
            if keyword in query:
                score += 8
            score += len(qtokens & tokens(keyword)) * 2
        if score > best_score:
            best_score = score
            best = item
    return best if best_score >= 4 else None

def generate_reply(message: str) -> str:
    query = normalize(message)

    if not query:
        return "Please enter a question about SkillTwin."

    if any(word in query.split() for word in {"hi", "hello", "hey"}):
        return (
            "Hello! 👋 I’m the SkillTwin Assistant.\n\n"
            "Ask me about SkillTwin, services, solutions, portals, "
            "assessments, learning, analytics or pricing."
        )

    if "what is skilltwin" in query or query in {"skilltwin", "about skilltwin"}:
        d = KNOWLEDGE["skilltwin"]
        return (
            f"**{d['name']}** is a {d['category']}.\n\n"
            f"{d['description']}\n\n"
            "**Core workflow**\n"
            f"{bullets(d['workflow'])}"
        )

    if any(x in query for x in ["how does skilltwin work", "how it works", "workflow", "process"]):
        return (
            "SkillTwin follows a continuous competency-improvement cycle:\n\n"
            f"{bullets(KNOWLEDGE['skilltwin']['workflow'])}\n\n"
            "The purpose is to turn competency gaps into measurable improvement."
        )

    if any(x in query for x in ["service", "services", "what do you provide", "capabilities"]):
        out = "**SkillTwin Services & Capabilities**\n\n"
        for item in KNOWLEDGE["services"]["items"]:
            out += f"**{item['name']}**\n{item['description']}\n\n"
        return out.strip()

    if any(x in query for x in ["pricing", "price", "cost", "plan", "plans", "subscription"]):
        d = KNOWLEDGE["pricing"]
        return (
            f"**SkillTwin Pricing**\n\n{d['status_message']}\n\n"
            "For organization-specific pricing, requirements, users, modules, analytics "
            "and integrations can be discussed with the SkillTwin team."
        )

    portal_map = {
        "trainee": "trainee",
        "trainer": "trainer",
        "institution": "institution",
        "college": "institution",
        "university": "institution",
        "industry": "industry",
        "company": "industry",
        "organization": "industry",
        "admin": "admin",
    }

    for keyword, key in portal_map.items():
        if keyword in query:
            d = KNOWLEDGE["portals"][key]
            return (
                f"**{d['name']}**\n\n{d['description']}\n\n"
                f"**Key capabilities**\n{bullets(d['capabilities'])}"
            )

    if any(x in query for x in ["solution", "solutions", "students", "college", "workforce"]):
        out = "**SkillTwin Solutions**\n\n"
        for item in KNOWLEDGE["solutions"]["items"]:
            out += f"**{item['audience']}**\n{item['description']}\n{bullets(item['capabilities'])}\n\n"
        return out.strip()

    if any(x in query for x in ["technology", "technologies", "tech stack", "built with"]):
        return (
            "**SkillTwin Technology**\n\n"
            "The current platform uses React/Vite/Tailwind on the frontend "
            "and Python/FastAPI with SQLAlchemy and MariaDB on the backend, "
            "with JWT-based authentication and role-based authorization."
        )

    faq = best_faq_match(query)
    if faq:
        return faq["answer"]

        return (
        "I don’t have verified information for that in my current "
        "SkillTwin knowledge base.\n\n"
        "Try asking about:\n\n"
        "• SkillTwin\n"
        "• Services\n"
        "• Solutions\n"
        "• Assessments\n"
        "• Skill-gap analysis\n"
        "• Learning paths\n"
        "• Portals\n"
        "• Certification\n"
        "• Analytics\n"
        "• Pricing"
    )
