from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.trainee import Trainee
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.payment import Payment


router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
)


def get_trainee(
    current_user: User,
    db: Session,
) -> Trainee:

    trainee = db.scalar(
        select(Trainee).where(
            Trainee.user_id == current_user.id
        )
    )

    if not trainee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainee profile not found",
        )

    return trainee


class DemoPaymentRequest(BaseModel):
    course_id: int


@router.post("/demo/create")
def create_demo_payment(
    payload: DemoPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    trainee = get_trainee(current_user, db)

    course = db.scalar(
        select(Course).where(
            Course.id == payload.course_id,
            Course.is_active.is_(True),
        )
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    existing_enrollment = db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.trainee_id == trainee.id,
            CourseEnrollment.course_id == course.id,
        )
    )

    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already enrolled in this course.",
        )

    order_id = (
        f"DEMO-ORDER-{uuid4().hex[:12].upper()}"
    )

    payment_id = (
        f"DEMO-PAY-{uuid4().hex[:12].upper()}"
    )

    payment = Payment(
        trainee_id=trainee.id,
        course_id=course.id,
        amount_paise=course.price_paise,
        currency=course.currency,
        gateway="demo",
        gateway_order_id=order_id,
        gateway_payment_id=payment_id,
        status="successful",
        paid_at=datetime.utcnow(),
    )

    db.add(payment)
    db.flush()

    enrollment = CourseEnrollment(
        trainee_id=trainee.id,
        course_id=course.id,
        status="in_progress",
        enrolled_at=datetime.utcnow(),
    )

    db.add(enrollment)

    db.commit()

    db.refresh(payment)
    db.refresh(enrollment)

    return {
        "success": True,
        "message": "Demo payment successful.",
        "payment_id": payment.id,
        "order_id": order_id,
        "transaction_id": payment_id,
        "enrollment_id": enrollment.id,
        "course_id": course.id,
        "course_title": course.title,
        "amount_paise": course.price_paise,
        "currency": course.currency,
    }