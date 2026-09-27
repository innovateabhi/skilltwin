from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.course_domain import CourseDomain
from app.models.course_category import CourseCategory


MARKETPLACE_DATA = [
    {
        "slug": "technology",
        "name": "Technology",
        "description": "Technology, software, computing, infrastructure, data, AI, and digital technologies.",
        "categories": [
            ("software-engineering", "Software Engineering"),
            ("programming", "Programming"),
            ("web-development", "Web Development"),
            ("mobile-development", "Mobile Development"),
            ("cloud-computing", "Cloud Computing"),
            ("devops-infrastructure", "DevOps & Infrastructure"),
            ("cybersecurity", "Cybersecurity"),
            ("data-databases", "Data & Databases"),
            ("data-science-analytics", "Data Science & Analytics"),
            ("artificial-intelligence-machine-learning", "Artificial Intelligence & Machine Learning"),
            ("robotics-embedded-systems", "Robotics & Embedded Systems"),
        ],
    },
    {
        "slug": "engineering",
        "name": "Engineering",
        "description": "Engineering disciplines and applied technical fields.",
        "categories": [
            ("mechanical-engineering", "Mechanical Engineering"),
            ("electrical-engineering", "Electrical Engineering"),
            ("electronics-engineering", "Electronics Engineering"),
            ("civil-engineering", "Civil Engineering"),
            ("chemical-engineering", "Chemical Engineering"),
            ("industrial-engineering", "Industrial Engineering"),
            ("automotive-engineering", "Automotive Engineering"),
            ("aerospace-engineering", "Aerospace Engineering"),
            ("biomedical-engineering", "Biomedical Engineering"),
            ("environmental-engineering", "Environmental Engineering"),
            ("mechatronics", "Mechatronics"),
            ("manufacturing-engineering", "Manufacturing Engineering"),
            ("systems-engineering", "Systems Engineering"),
        ],
    },
    {
        "slug": "management",
        "name": "Management",
        "description": "Management, project leadership, and product management.",
        "categories": [
            ("management", "Management"),
            ("project-management", "Project Management"),
            ("product-management", "Product Management"),
        ],
    },
    {
        "slug": "business",
        "name": "Business",
        "description": "Business strategy, entrepreneurship, and organizational growth.",
        "categories": [
            ("business-strategy", "Business & Strategy"),
            ("entrepreneurship", "Entrepreneurship"),
        ],
    },
    {
        "slug": "finance",
        "name": "Finance",
        "description": "Finance, accounting, investment, and financial management.",
        "categories": [
            ("finance-accounting", "Finance & Accounting"),
        ],
    },
    {
        "slug": "marketing",
        "name": "Marketing",
        "description": "Marketing, sales, branding, and customer growth.",
        "categories": [
            ("marketing-sales", "Marketing & Sales"),
        ],
    },
    {
        "slug": "hr",
        "name": "HR",
        "description": "Human resources, talent, people operations, and development.",
        "categories": [
            ("human-resources", "Human Resources"),
        ],
    },
    {
        "slug": "design",
        "name": "Design",
        "description": "Design, user experience, visual communication, and creative technologies.",
        "categories": [
            ("ui-ux-design", "UI/UX & Design"),
        ],
    },
    {
        "slug": "healthcare",
        "name": "Healthcare",
        "description": "Healthcare, life sciences, health technology, and healthcare operations.",
        "categories": [
            ("healthcare-life-sciences", "Healthcare & Life Sciences"),
        ],
    },
    {
        "slug": "legal-compliance",
        "name": "Legal & Compliance",
        "description": "Legal, compliance, governance, privacy, and regulatory topics.",
        "categories": [
            ("legal-compliance", "Legal & Compliance"),
        ],
    },
    {
        "slug": "education",
        "name": "Education",
        "description": "Education, teaching, learning, training, and instructional design.",
        "categories": [
            ("education-training", "Education & Training"),
        ],
    },
    {
        "slug": "operations",
        "name": "Operations",
        "description": "Operations management, process improvement, and organizational operations.",
        "categories": [
            ("operations-management", "Operations Management"),
        ],
    },
    {
        "slug": "supply-chain",
        "name": "Supply Chain",
        "description": "Supply chain, procurement, logistics, and quality management.",
        "categories": [
            ("supply-chain-logistics", "Supply Chain & Logistics"),
        ],
    },
    {
        "slug": "construction",
        "name": "Construction",
        "description": "Architecture, construction, BIM, planning, and built environments.",
        "categories": [
            ("architecture-construction", "Architecture & Construction"),
        ],
    },
    {
        "slug": "energy",
        "name": "Energy",
        "description": "Energy systems, sustainability, and environmental responsibility.",
        "categories": [
            ("energy-sustainability", "Energy & Sustainability"),
        ],
    },
    {
        "slug": "research",
        "name": "Research",
        "description": "Research, scientific methods, academia, and research practices.",
        "categories": [
            ("research-academia", "Research & Academia"),
        ],
    },
    {
        "slug": "professional-skills",
        "name": "Professional Skills",
        "description": "Professional effectiveness, communication, leadership, and workplace skills.",
        "categories": [
            ("communication", "Communication"),
            ("leadership", "Leadership"),
            ("critical-thinking", "Critical Thinking"),
            ("problem-solving", "Problem Solving"),
            ("professional-skills", "Professional Skills"),
            ("workplace-skills", "Workplace Skills"),
        ],
    },
    {
        "slug": "digital-skills",
        "name": "Digital Skills",
        "description": "Digital literacy and essential digital workplace capabilities.",
        "categories": [
            ("digital-literacy", "Digital Literacy"),
        ],
    },
]


def seed_marketplace():
    db = SessionLocal()

    try:
        created_domains = 0
        created_categories = 0

        for domain_index, domain_data in enumerate(MARKETPLACE_DATA, start=1):

            domain = db.scalar(
                select(CourseDomain).where(
                    CourseDomain.slug == domain_data["slug"]
                )
            )

            if not domain:
                domain = CourseDomain(
                    slug=domain_data["slug"],
                    name=domain_data["name"],
                    description=domain_data["description"],
                    display_order=domain_index,
                    is_active=True,
                )

                db.add(domain)
                db.flush()

                created_domains += 1

            for category_index, (slug, name) in enumerate(
                domain_data["categories"],
                start=1,
            ):

                category = db.scalar(
                    select(CourseCategory).where(
                        CourseCategory.slug == slug
                    )
                )

                if category:
                    continue

                category = CourseCategory(
                    domain_id=domain.id,
                    slug=slug,
                    name=name,
                    description=f"{name} courses and learning resources.",
                    display_order=category_index,
                    is_active=True,
                )

                db.add(category)
                created_categories += 1

        db.commit()

        print()
        print("Course marketplace catalog seeded.")
        print(f"Domains created   : {created_domains}")
        print(f"Categories created: {created_categories}")
        print()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_marketplace()