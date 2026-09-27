from datetime import datetime
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.trainer import (
    TrainerProfileUpdate,
    QuestionnaireCreate,
    QuestionnaireQuestionCreate,
    CompetencyCreate,
    NotificationCreate,
)
from app.services.trainer_service import (
    table_exists,
    table_columns,
    pick,
    qident,
    trainer_required,
    current_user_id,
    get_trainer_row,
    insert_dynamic,
    update_dynamic,
    safe_count,
)

router = APIRouter(prefix="/api/trainer", tags=["Trainer Portal"])

UPLOAD_ROOT = Path("uploads/trainer")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _current(db, current_user):
    return trainer_required(db, current_user)


# The build_trainer_router() factory below is the router to register.

# -------------------------------------------------------------------
# The implementation below is exposed through factory functions so
# integration with an existing Auth dependency is a one-line change.
# -------------------------------------------------------------------

def build_trainer_router(get_current_user):
    api = APIRouter(prefix="/api/trainer", tags=["Trainer Portal"])

    def current(db, user):
        return trainer_required(db, user)

    @api.get("/me")
    def me(db: Session = Depends(get_db), user=Depends(get_current_user)):
        uid, trainer = current(db, user)
        return {"user_id": uid, "trainer": dict(trainer)}

    @api.get("/dashboard")
    def dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
        uid, trainer = current(db, user)
        tcols = table_columns(db, "trainers")
        trainer_id = trainer.get(pick(tcols, "id", "trainer_id"))

        course_count = 0
        trainee_count = 0
        assessment_count = 0
        resource_count = safe_count(
            db, "trainer_resources",
            "`trainer_id` = :tid", {"tid": trainer_id}
        )
        questionnaire_count = safe_count(
            db, "trainer_questionnaires",
            "`trainer_id` = :tid", {"tid": trainer_id}
        )

        if table_exists(db, "courses") and trainer_id is not None:
            c = table_columns(db, "courses")
            trainer_col = pick(c, "trainer_id", "created_by", "instructor_id", "owner_id")
            if trainer_col:
                course_count = safe_count(
                    db, "courses", f"{qident(trainer_col)} = :tid",
                    {"tid": trainer_id}
                )

        if table_exists(db, "course_enrollments") and trainer_id is not None and table_exists(db, "courses"):
            ec = table_columns(db, "course_enrollments")
            cc = table_columns(db, "courses")
            eid = pick(ec, "course_id")
            c_id = pick(cc, "id", "course_id")
            c_trainer = pick(cc, "trainer_id", "created_by", "instructor_id", "owner_id")
            if eid and c_id and c_trainer:
                sql = text(
                    f"SELECT COUNT(DISTINCT e.user_id) AS c "
                    f"FROM `course_enrollments` e "
                    f"JOIN `courses` c ON e.{qident(eid)} = c.{qident(c_id)} "
                    f"WHERE c.{qident(c_trainer)} = :tid"
                )
                try:
                    trainee_count = int(db.execute(sql, {"tid": trainer_id}).scalar() or 0)
                except Exception:
                    trainee_count = 0

        if table_exists(db, "assessments") and trainer_id is not None:
            ac = table_columns(db, "assessments")
            trainer_col = pick(ac, "trainer_id", "created_by", "owner_id")
            if trainer_col:
                assessment_count = safe_count(
                    db, "assessments",
                    f"{qident(trainer_col)} = :tid",
                    {"tid": trainer_id}
                )

        name = (
            trainer.get(pick(tcols, "full_name", "name"))
            or trainer.get("first_name")
            or "Trainer"
        )

        return {
            "trainer": dict(trainer),
            "stats": {
                "courses": course_count,
                "trainees": trainee_count,
                "assessments": assessment_count,
                "resources": resource_count,
                "questionnaires": questionnaire_count,
            },
        }

    @api.put("/profile")
    def update_profile(
        payload: TrainerProfileUpdate,
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        cols = table_columns(db, "trainers")
        id_col = pick(cols, "id", "trainer_id")
        if not id_col:
            raise HTTPException(500, "Trainer table has no id column")

        update_dynamic(
            db,
            "trainers",
            id_col,
            trainer[id_col],
            {
                "full_name": payload.full_name,
                "name": payload.full_name,
                "phone": payload.phone,
                "designation": payload.designation,
                "organization": payload.organization,
                "experience_years": payload.experience_years,
                "experience": payload.experience_years,
                "expertise": payload.expertise,
                "qualifications": payload.qualifications,
                "bio": payload.bio,
                "updated_at": datetime.utcnow(),
            },
        )
        return {"message": "Trainer profile updated"}

    @api.get("/courses")
    def courses(
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))
        if not table_exists(db, "courses"):
            return []

        cc = table_columns(db, "courses")
        trainer_col = pick(cc, "trainer_id", "created_by", "instructor_id", "owner_id")
        if not trainer_col:
            return []

        rows = db.execute(
            text(
                f"SELECT * FROM `courses` "
                f"WHERE {qident(trainer_col)} = :tid "
                f"ORDER BY id DESC"
            ),
            {"tid": tid},
        ).mappings().all()
        return [dict(r) for r in rows]

    @api.get("/trainees")
    def trainees(
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))

        if not table_exists(db, "courses") or not table_exists(db, "course_enrollments"):
            return []

        cc = table_columns(db, "courses")
        ec = table_columns(db, "course_enrollments")
        trainer_col = pick(cc, "trainer_id", "created_by", "instructor_id", "owner_id")
        course_id = pick(cc, "id", "course_id")
        enroll_course = pick(ec, "course_id")
        enroll_user = pick(ec, "user_id", "trainee_id")

        if not all([trainer_col, course_id, enroll_course, enroll_user]):
            return []

        # Return enrollment rows plus course information. The frontend can
        # use this as the real trainee roster.
        sql = text(
            f"SELECT e.*, c.* "
            f"FROM `course_enrollments` e "
            f"JOIN `courses` c ON e.{qident(enroll_course)} = c.{qident(course_id)} "
            f"WHERE c.{qident(trainer_col)} = :tid "
            f"ORDER BY e.id DESC"
        )
        return [dict(r) for r in db.execute(sql, {"tid": tid}).mappings().all()]

    @api.get("/questionnaires")
    def questionnaires(
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))
        if not table_exists(db, "trainer_questionnaires"):
            return []
        rows = db.execute(
            text(
                "SELECT * FROM trainer_questionnaires "
                "WHERE trainer_id = :tid ORDER BY created_at DESC"
            ),
            {"tid": tid},
        ).mappings().all()
        return [dict(r) for r in rows]

    @api.post("/questionnaires")
    def create_questionnaire(
        payload: QuestionnaireCreate,
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))

        qid = insert_dynamic(
            db,
            "trainer_questionnaires",
            {
                "trainer_id": tid,
                "title": payload.title,
                "description": payload.description,
                "deadline": payload.deadline,
                "course_id": payload.course_id,
                "status": "open",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )
        db.commit()
        return {"id": qid, "message": "Questionnaire created"}

    @api.post("/questionnaires/{questionnaire_id}/questions")
    def add_question(
        questionnaire_id: int,
        payload: QuestionnaireQuestionCreate,
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        if not table_exists(db, "trainer_questionnaire_questions"):
            raise HTTPException(500, "Questionnaire questions table is missing")
        qid = insert_dynamic(
            db,
            "trainer_questionnaire_questions",
            {
                "questionnaire_id": questionnaire_id,
                "question": payload.question,
                "options_json": __import__("json").dumps(payload.options),
                "correct_answer": payload.correct_answer,
                "marks": payload.marks,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
        return {"id": qid}

    @api.get("/library")
    def library(
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))
        if not table_exists(db, "trainer_resources"):
            return []
        rows = db.execute(
            text(
                "SELECT * FROM trainer_resources "
                "WHERE trainer_id = :tid ORDER BY created_at DESC"
            ),
            {"tid": tid},
        ).mappings().all()
        return [dict(r) for r in rows]

    @api.post("/library/upload")
    async def upload_resource(
        title: str = Form(...),
        resource_type: str = Form("document"),
        description: str | None = Form(None),
        course_id: int | None = Form(None),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))

        suffix = Path(file.filename or "").suffix.lower()
        stored = f"{uuid.uuid4().hex}{suffix}"
        target_dir = UPLOAD_ROOT / str(tid)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / stored

        with target.open("wb") as out:
            shutil.copyfileobj(file.file, out)

        rid = insert_dynamic(
            db,
            "trainer_resources",
            {
                "trainer_id": tid,
                "title": title,
                "resource_type": resource_type,
                "description": description,
                "course_id": course_id,
                "original_filename": file.filename,
                "stored_filename": stored,
                "file_path": str(target).replace("\\", "/"),
                "mime_type": file.content_type,
                "file_size": target.stat().st_size,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
        return {"id": rid, "message": "Resource uploaded"}

    @api.delete("/library/{resource_id}")
    def delete_resource(
        resource_id: int,
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))

        row = db.execute(
            text(
                "SELECT * FROM trainer_resources "
                "WHERE id = :rid AND trainer_id = :tid LIMIT 1"
            ),
            {"rid": resource_id, "tid": tid},
        ).mappings().first()
        if not row:
            raise HTTPException(404, "Resource not found")

        path = row.get("file_path")
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

        db.execute(
            text("DELETE FROM trainer_resources WHERE id=:rid AND trainer_id=:tid"),
            {"rid": resource_id, "tid": tid},
        )
        db.commit()
        return {"message": "Resource deleted"}

    @api.get("/competencies")
    def competencies(
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))
        if not table_exists(db, "trainer_competencies"):
            return []
        rows = db.execute(
            text(
                "SELECT * FROM trainer_competencies "
                "WHERE trainer_id=:tid ORDER BY id DESC"
            ),
            {"tid": tid},
        ).mappings().all()
        return [dict(r) for r in rows]

    @api.post("/competencies")
    def add_competency(
        payload: CompetencyCreate,
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))
        cid = insert_dynamic(
            db,
            "trainer_competencies",
            {
                "trainer_id": tid,
                "competency_id": payload.competency_id,
                "competency_name": payload.competency_name,
                "level": payload.level,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
        return {"id": cid}

    @api.delete("/competencies/{item_id}")
    def delete_competency(
        item_id: int,
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        tc = table_columns(db, "trainers")
        tid = trainer.get(pick(tc, "id", "trainer_id"))
        db.execute(
            text(
                "DELETE FROM trainer_competencies "
                "WHERE id=:id AND trainer_id=:tid"
            ),
            {"id": item_id, "tid": tid},
        )
        db.commit()
        return {"message": "Competency removed"}

    @api.get("/notifications")
    def notifications(
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        if not table_exists(db, "trainer_notifications"):
            return []
        rows = db.execute(
            text(
                "SELECT * FROM trainer_notifications "
                "WHERE recipient_user_id=:uid OR recipient_user_id IS NULL "
                "ORDER BY created_at DESC"
            ),
            {"uid": uid},
        ).mappings().all()
        return [dict(r) for r in rows]

    @api.patch("/notifications/{notification_id}/read")
    def read_notification(
        notification_id: int,
        db: Session = Depends(get_db),
        user=Depends(get_current_user),
    ):
        uid, trainer = current(db, user)
        db.execute(
            text(
                "UPDATE trainer_notifications SET is_read=1 "
                "WHERE id=:id AND recipient_user_id=:uid"
            ),
            {"id": notification_id, "uid": uid},
        )
        db.commit()
        return {"message": "Notification marked as read"}

    return api
