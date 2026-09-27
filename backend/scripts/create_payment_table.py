from app.core.database import Base, engine

from app.models import Payment


def main():
    Base.metadata.create_all(bind=engine)
    print("Payment table created successfully.")


if __name__ == "__main__":
    main()