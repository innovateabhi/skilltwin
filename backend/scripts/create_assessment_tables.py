from app.core.database import Base, engine

# Import every model so SQLAlchemy knows about them.
import app.models  # noqa: F401


if __name__ == "__main__":
    print("=" * 60)
    print("Creating SkillTwin assessment tables")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)

    print()
    print("Assessment tables are ready.")