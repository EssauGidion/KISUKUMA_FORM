
# ============================================================
# KISUKUMA FORM
# MAIN.PY
#
# FastAPI application for collecting:
#
# Kiswahili -> Kisukuma
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

from fastapi import (
    FastAPI,
    Request,
    Depends,
    UploadFile,
    File,
)

from fastapi.responses import (
    RedirectResponse,
    StreamingResponse,
)

from fastapi.staticfiles import StaticFiles

from fastapi.templating import (
    Jinja2Templates,
)

from sqlalchemy.orm import Session
from sqlalchemy import and_, exists, func, inspect, text

import pandas as pd
import random
import io
import os
import uuid


# ============================================================
# DATABASE
# ============================================================

from .database import (
    Base,
    engine,
    get_db,
)


# ============================================================
# MODELS
# ============================================================

from .models import (
    Sentence,
    Response,
    Tribe,
    LanguageDataset,
)


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(
    bind=engine
)

# Keep existing SQLite installations compatible with the new optional fields.
if "responses" in inspect(engine).get_table_names():
    columns = {column["name"] for column in inspect(engine).get_columns("responses")}
    with engine.begin() as connection:
        if "tribe" not in columns:
            connection.execute(text("ALTER TABLE responses ADD COLUMN tribe VARCHAR(50)"))
        if "target_language" not in columns:
            connection.execute(text("ALTER TABLE responses ADD COLUMN target_language VARCHAR(50)"))

TRIBES = [
    {"name": "Kisukuma", "language_code": "kisukuma", "image": "wasukuma.png"},
    {"name": "Kihaya", "language_code": "kihaya", "image": "wahaya.jpg"},
    {"name": "Kinyakyusa", "language_code": "kinyakyusa", "image": "wanyakyusa.png"},
    {"name": "Kiha", "language_code": "kiha", "image": "waha.png"},
    {"name": "Kihehe", "language_code": "kihehe", "image": "wahehe.png"},
    {"name": "Wachaga", "language_code": "kichaga", "image": "wachaga.png"},
    {"name": "Wagogo", "language_code": "kigogo", "image": "wagogo.png"},
    {"name": "Wajita", "language_code": "kijita", "image": "wajita.png"},
    {"name": "Wanyamwezi", "language_code": "kinyamwezi", "image": "wanyamwezi.png"},
    {"name": "Wakurya", "language_code": "kikurya", "image": "wakurya.png"},
    {"name": "Wazaramo", "language_code": "kizaramo", "image": "wazaramo.png"},
    {"name": "Wamakonde", "language_code": "kimakonde", "image": "wamakonde.png"},
]

seed_db = next(get_db())
try:
    for item in TRIBES:
        if not seed_db.query(Tribe).filter_by(name=item["name"]).first():
            seed_db.add(Tribe(**item))
    for item in TRIBES:
        dataset_name = f"Kiswahili - {item['language_code']}"
        if not seed_db.query(LanguageDataset).filter_by(name=dataset_name).first():
            seed_db.add(LanguageDataset(
                name=dataset_name,
                source_language="kiswahili",
                target_language=item["language_code"],
                filename=f"{item['language_code']}_dataset.csv",
            ))
    seed_db.commit()
finally:
    seed_db.close()


# ============================================================
# CREATE FASTAPI APP
# ============================================================

app = FastAPI(

    title="Kisukuma Translation Form",

    description=(
        "System for collecting "
        "Kiswahili to Kisukuma "
        "translation data."
    ),

    version="1.0.0",
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(

    "/static",

    StaticFiles(
        directory="app/static"
    ),

    name="static",
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(

    directory="app/templates"

)


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def home():

    return RedirectResponse(
        url="/form"
    )


# ============================================================
# FORM PAGE
# ============================================================

@app.get("/form")
def show_form(

    request: Request,

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # Count sentences
    # --------------------------------------------------------

    selected_tribe = request.query_params.get("tribe")
    tribe = (
        db.query(Tribe).filter(Tribe.name == selected_tribe).first()
        if selected_tribe
        else None
    )
    tribes = db.query(Tribe).order_by(Tribe.id).all()

    if tribe is None:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "sentences": [],
                "participant_id": "",
                "tribes": tribes,
                "selected_tribe": None,
                "error": None,
            },
        )

    available_sentence_query = db.query(Sentence).filter(
        ~exists().where(and_(
            Response.kiswahili == Sentence.kiswahili,
            Response.target_language == tribe.language_code,
        ))
    )
    sentence_count = available_sentence_query.count()


    # --------------------------------------------------------
    # Get sentence IDs
    # --------------------------------------------------------

    sentence_ids = [
        row[0]
        for row in available_sentence_query.with_entities(Sentence.id).all()
    ]


    # --------------------------------------------------------
    # Choose random 10
    # --------------------------------------------------------

    selected_ids = random.sample(

        sentence_ids,

        min(10, len(sentence_ids))

    )


    # --------------------------------------------------------
    # Get sentences
    # --------------------------------------------------------

    sentences = (

        db.query(Sentence)

        .filter(
            Sentence.id.in_(
                selected_ids
            )
        )

        .all()

    )


    # --------------------------------------------------------
    # Preserve random order
    # --------------------------------------------------------

    sentence_dict = {

        sentence.id: sentence

        for sentence in sentences

    }


    sentences = [

        sentence_dict[sentence_id]

        for sentence_id in selected_ids

    ]


    # --------------------------------------------------------
    # Create participant ID
    # --------------------------------------------------------

    participant_id = str(
        uuid.uuid4()
    )


    # --------------------------------------------------------
    # Display form
    # --------------------------------------------------------

    return templates.TemplateResponse(

        request=request,

        name="index.html",

        context={

            "sentences": sentences,

            "participant_id":
                participant_id,

            "error": None,
            "tribes": tribes,
            "selected_tribe": tribe,

        },

    )


# ============================================================
# SUBMIT FORM
# ============================================================

@app.post("/submit")
async def submit_form(

    request: Request,

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # Get form
    # --------------------------------------------------------

    form_data = await request.form()


    # --------------------------------------------------------
    # Participant ID and selected language
    # --------------------------------------------------------

    participant_id = (

        form_data.get(
            "participant_id"
        )

    )


    if not participant_id:

        participant_id = str(
            uuid.uuid4()
        )

    tribe_name = form_data.get("tribe")
    if not tribe_name:
        return RedirectResponse(url="/form", status_code=303)

    tribe = db.query(Tribe).filter(Tribe.name == tribe_name).first()
    if not tribe:
        return RedirectResponse(url="/form", status_code=303)


    # --------------------------------------------------------
    # Counter
    # --------------------------------------------------------

    saved = 0


    # --------------------------------------------------------
    # Process questions
    # --------------------------------------------------------

    for key, value in form_data.items():


        # ----------------------------------------------------
        # Only question fields
        # ----------------------------------------------------

        if not key.startswith(
            "question_"
        ):

            continue


        # ----------------------------------------------------
        # Get ID
        # ----------------------------------------------------

        try:

            sentence_id = int(

                key.replace(
                    "question_",
                    ""
                )

            )

        except ValueError:

            continue


        # ----------------------------------------------------
        # Kisukuma answer
        # ----------------------------------------------------

        kisukuma_answer = str(
            value
        ).strip()


        # ----------------------------------------------------
        # Ignore empty answer
        # ----------------------------------------------------

        if not kisukuma_answer:

            continue


        # ----------------------------------------------------
        # Find sentence
        # ----------------------------------------------------

        sentence = (

            db.query(Sentence)

            .filter(
                Sentence.id ==
                sentence_id
            )

            .first()

        )


        if not sentence:

            continue

        already_answered = db.query(Response.id).filter(
            Response.kiswahili == sentence.kiswahili,
            Response.target_language == tribe.language_code,
        ).first()
        if already_answered:
            continue


        # ----------------------------------------------------
        # Create response
        # ----------------------------------------------------

        response = Response(

            kiswahili=(
                sentence.kiswahili
            ),

            kisukuma=(
                kisukuma_answer
            ),

            participant_id=(
                participant_id
            ),
            tribe=tribe.name if tribe else "Kisukuma",
            target_language=tribe.language_code if tribe else "kisukuma",

        )


        db.add(response)

        saved += 1


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    db.commit()


    # --------------------------------------------------------
    # Success page
    # --------------------------------------------------------

    return templates.TemplateResponse(

        request=request,

        name="success.html",

        context={

            "saved": saved,

        },

    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.get("/admin")
def admin_dashboard(

    request: Request,

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # Count sentences
    # --------------------------------------------------------

    total_sentence_count = (
        db.query(
            Sentence
        ).count()
    )


    # --------------------------------------------------------
    # Count responses
    # --------------------------------------------------------

    response_count = (

        db.query(
            Response
        ).count()

    )

    tribes = db.query(Tribe).order_by(Tribe.id).all()
    datasets = db.query(LanguageDataset).order_by(LanguageDataset.id).all()
    response_counts = dict(
        db.query(
            Response.target_language,
            func.count(Response.id),
        )
        .filter(Response.target_language.isnot(None))
        .group_by(Response.target_language)
        .all()
    )
    completed_pairs = db.query(
        Response.kiswahili,
        Response.target_language,
    ).filter(Response.target_language.isnot(None)).distinct().all()
    completed_languages = {}
    for sentence_text, language_code in completed_pairs:
        completed_languages.setdefault(sentence_text, set()).add(language_code)
    sentence_texts = db.query(Sentence.kiswahili).distinct().all()
    completed_sentence_count = sum(
        len(completed_languages.get(sentence_text, set())) >= len(tribes)
        for (sentence_text,) in sentence_texts
    )
    sentence_count = total_sentence_count - completed_sentence_count


    # --------------------------------------------------------
    # Latest responses
    # --------------------------------------------------------

    responses = (

        db.query(Response)

        .order_by(
            Response.id.desc()
        )

        .limit(20)

        .all()

    )


    # --------------------------------------------------------
    # Dashboard
    # --------------------------------------------------------

    return templates.TemplateResponse(

        request=request,

        name="admin.html",

        context={

            "sentence_count":
                sentence_count,
            "sentence_total":
                total_sentence_count,

            "response_count":
                response_count,

            "responses":
                responses,
            "tribes": tribes,
            "datasets": datasets,
            "response_counts": response_counts,

        },

    )


# ============================================================
# CSV UPLOAD
# ============================================================

@app.post("/admin/upload")
async def upload_csv(

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not file.filename:

        return {

            "error":
                "Tafadhali chagua CSV file."

        }


    # --------------------------------------------------------
    # Check extension
    # --------------------------------------------------------

    if not file.filename.lower().endswith(
        ".csv"
    ):

        return {

            "error":
                "File lazima iwe CSV."

        }


    try:

        # ----------------------------------------------------
        # Read file
        # ----------------------------------------------------

        contents = await file.read()


        # ----------------------------------------------------
        # Read CSV
        # ----------------------------------------------------

        df = pd.read_csv(

            io.BytesIO(contents)

        )


        # ----------------------------------------------------
        # Clean columns
        # ----------------------------------------------------

        df.columns = [

            str(column).strip()

            for column in df.columns

        ]


        # ----------------------------------------------------
        # Possible columns
        # ----------------------------------------------------

        possible_columns = [

            "kiswahili",

            "Kiswahili",

            "Swahili",

            "swahili",

            "Swahili Translation",

            "swahili translation",

            "Swahili_Translation",

        ]


        selected_column = None


        # ----------------------------------------------------
        # Find column
        # ----------------------------------------------------

        for column in possible_columns:

            if column in df.columns:

                selected_column = column

                break


        # ----------------------------------------------------
        # Column missing
        # ----------------------------------------------------

        if selected_column is None:

            return {

                "error": (

                    "CSV yako haina column "
                    "ya Kiswahili."

                ),

                "available_columns":
                    df.columns.tolist(),

            }


        # ----------------------------------------------------
        # Keep column
        # ----------------------------------------------------

        df = df[
            [selected_column]
        ].copy()


        df.columns = [
            "kiswahili"
        ]


        # ----------------------------------------------------
        # Clean text
        # ----------------------------------------------------

        df["kiswahili"] = (

            df["kiswahili"]

            .fillna("")

            .astype(str)

            .str.strip()

        )


        # ----------------------------------------------------
        # Remove empty
        # ----------------------------------------------------

        df = df[
            df["kiswahili"] != ""
        ]


        # ----------------------------------------------------
        # Remove duplicates
        # ----------------------------------------------------

        df = df.drop_duplicates(

            subset=[
                "kiswahili"
            ]

        )


        # ----------------------------------------------------
        # Records
        # ----------------------------------------------------

        records = df.to_dict(

            orient="records"

        )


        # ----------------------------------------------------
        # Insert database
        # ----------------------------------------------------

        batch_size = 5000


        for start in range(

            0,

            len(records),

            batch_size

        ):

            batch = records[

                start:
                start + batch_size

            ]


            db.bulk_insert_mappings(

                Sentence,

                batch

            )


        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        db.commit()


        # ----------------------------------------------------
        # Redirect
        # ----------------------------------------------------

        return RedirectResponse(

            url="/admin",

            status_code=303

        )


    except Exception as e:

        db.rollback()


        return {

            "error": (
                "Kuna tatizo wakati "
                "wa ku-import CSV."
            ),

            "details": str(e),

        }


# ============================================================
# IMPORT DEFAULT CSV
# ============================================================

@app.get("/admin/import")
def import_default_csv(

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # CSV path
    # --------------------------------------------------------

    csv_path = os.path.join(

        "dataset",

        "sentences.csv"

    )


    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not os.path.exists(
        csv_path
    ):

        return {

            "error": (

                "CSV haijapatikana: "

                f"{csv_path}"

            )

        }


    try:

        # ----------------------------------------------------
        # Read CSV
        # ----------------------------------------------------

        df = pd.read_csv(
            csv_path
        )


        # ----------------------------------------------------
        # Clean columns
        # ----------------------------------------------------

        df.columns = [

            str(column).strip()

            for column in df.columns

        ]


        # ----------------------------------------------------
        # Possible columns
        # ----------------------------------------------------

        possible_columns = [

            "kiswahili",

            "Kiswahili",

            "Swahili",

            "swahili",

            "Swahili Translation",

            "swahili translation",

            "Swahili_Translation",

        ]


        selected_column = None


        for column in possible_columns:

            if column in df.columns:

                selected_column = column

                break


        # ----------------------------------------------------
        # Check column
        # ----------------------------------------------------

        if selected_column is None:

            return {

                "error": (
                    "Column ya Kiswahili "
                    "haijapatikana."
                ),

                "available_columns":
                    df.columns.tolist(),

            }


        # ----------------------------------------------------
        # Keep Kiswahili
        # ----------------------------------------------------

        df = df[
            [selected_column]
        ].copy()


        df.columns = [
            "kiswahili"
        ]


        # ----------------------------------------------------
        # Clean
        # ----------------------------------------------------

        df["kiswahili"] = (

            df["kiswahili"]

            .fillna("")

            .astype(str)

            .str.strip()

        )


        # ----------------------------------------------------
        # Remove empty
        # ----------------------------------------------------

        df = df[
            df["kiswahili"] != ""
        ]


        # ----------------------------------------------------
        # Remove duplicates
        # ----------------------------------------------------

        df = df.drop_duplicates(

            subset=[
                "kiswahili"
            ]

        )


        # ----------------------------------------------------
        # Records
        # ----------------------------------------------------

        records = df.to_dict(

            orient="records"

        )


        # ----------------------------------------------------
        # Insert
        # ----------------------------------------------------

        batch_size = 5000


        for start in range(

            0,

            len(records),

            batch_size

        ):

            batch = records[

                start:
                start + batch_size

            ]


            db.bulk_insert_mappings(

                Sentence,

                batch

            )


        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        db.commit()


        # ----------------------------------------------------
        # Count
        # ----------------------------------------------------

        total = (

            db.query(
                Sentence
            ).count()

        )


        return {

            "message": (
                "CSV imeingizwa "
                "kikamilifu."
            ),

            "sentences": total,

        }


    except Exception as e:

        db.rollback()


        return {

            "error": (
                "Kuna tatizo wakati "
                "wa ku-import CSV."
            ),

            "details": str(e),

        }


# ============================================================
# DOWNLOAD DATASET
# ============================================================

@app.get("/admin/download")
def download_dataset(

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # Get responses
    # --------------------------------------------------------

    responses = (

        db.query(Response)

        .order_by(
            Response.id.asc()
        )

        .all()

    )


    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    data = []


    for response in responses:

        data.append({

            "id":
                response.id,

            "kiswahili":
                response.kiswahili,

            "kisukuma":
                response.kisukuma,

            "participant_id":
                response.participant_id,
            "tribe": response.tribe or "Kisukuma",
            "target_language": response.target_language or "kisukuma",

        })


    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(

        data,

        columns=[

            "id",

            "kiswahili",

            "kisukuma",

            "participant_id",
            "tribe",
            "target_language",

        ],

    )


    # --------------------------------------------------------
    # Convert to CSV
    # --------------------------------------------------------

    output = io.StringIO()


    df.to_csv(

        output,

        index=False,

    )


    # --------------------------------------------------------
    # Convert bytes
    # --------------------------------------------------------

    csv_bytes = (

        output

        .getvalue()

        .encode(
            "utf-8-sig"
        )

    )


    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    return StreamingResponse(

        io.BytesIO(
            csv_bytes
        ),

        media_type="text/csv",

        headers={

            "Content-Disposition": (

                'attachment; '
                'filename='
                '"kisukuma_dataset.csv"'

            )


        },

    )


@app.get("/admin/download/{language_code}")
def download_language_dataset(
    language_code: str,
    db: Session = Depends(get_db),
):
    """Download responses for one Kiswahili-to-tribal-language dataset."""
    dataset = db.query(LanguageDataset).filter(
        LanguageDataset.target_language == language_code
    ).first()
    if not dataset:
        return {"error": "Dataset haijapatikana."}

    responses = db.query(Response).filter(
        Response.target_language == language_code
    ).order_by(Response.id.asc()).all()
    data = [{
        "id": item.id,
        "kiswahili": item.kiswahili,
        language_code: item.kisukuma,
        "participant_id": item.participant_id,
    } for item in responses]
    output = io.StringIO()
    pd.DataFrame(
        data,
        columns=["id", "kiswahili", language_code, "participant_id"],
    ).to_csv(output, index=False)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{dataset.filename}"'
        },
    )


@app.delete("/admin/delete-sentences")
def delete_sentences(
    db: Session = Depends(get_db),
):
    """Delete imported/uploaded sentence records without deleting responses."""
    try:
        deleted = db.query(Sentence).delete(synchronize_session=False)
        db.commit()
        return {
            "success": True,
            "deleted": deleted,
            "message": f"Sentensi {deleted} zimefutwa kikamilifu.",
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": "Kuna tatizo wakati wa kufuta sentensi.",
            "details": str(e),
        }


@app.delete("/admin/delete-dataset/{language_code}")
def delete_language_dataset(
    language_code: str,
    db: Session = Depends(get_db),
):
    """Delete collected responses for one language without deleting sentences."""
    dataset = db.query(LanguageDataset).filter(
        LanguageDataset.target_language == language_code
    ).first()
    if not dataset:
        return {
            "success": False,
            "error": "Dataset haijapatikana.",
        }

    try:
        deleted = db.query(Response).filter(
            Response.target_language == language_code
        ).delete(synchronize_session=False)
        db.commit()
        return {
            "success": True,
            "deleted": deleted,
            "message": f"Majibu {deleted} ya {language_code} yamefutwa.",
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": "Kuna tatizo wakati wa kufuta dataset.",
            "details": str(e),
        }


# ============================================================
# DELETE RESPONSE
# ============================================================

@app.delete("/admin/delete/{response_id}")
def delete_response(

    response_id: int,

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # Find response
    # --------------------------------------------------------

    response = (

        db.query(Response)

        .filter(
            Response.id == response_id
        )

        .first()

    )


    # --------------------------------------------------------
    # Check if exists
    # --------------------------------------------------------

    if not response:

        return {

            "success": False,

            "error": "Jibu halijapatikana."

        }


    try:

        # -------- ------------------------------------------------
        # Delete
        # --------------------------------------------------------

        db.delete(response)

        db.commit()


        return {

            "success": True,

            "message": (

                "Jibu limefutwa "

                "kikamilifu."

            )

        }


    except Exception as e:

        db.rollback()


        return {

            "success": False,

            "error": (

                "Kuna tatizo wakati "

                "wa kufuta jibu."

            ),

            "details": str(e),

        }


# ============================================================
# DELETE ALL RESPONSES
# ============================================================

@app.delete("/admin/delete-all")
def delete_all_responses(

    db: Session = Depends(get_db),

):

    try:

        deleted = db.query(Response).delete(
            synchronize_session=False
        )

        db.commit()


        return {

            "success": True,

            "deleted": deleted,

            "message": (

                f"Majibu {deleted} yamefutwa "

                "kikamilifu."

            )

        }


    except Exception as e:

        db.rollback()


        return {

            "success": False,

            "error": (

                "Kuna tatizo wakati "

                "wa kufuta majibu yote."

            ),

            "details": str(e),

        }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {

        "status": "ok",

        "message": (
            "Kisukuma Form API "
            "inafanya kazi."
        ),

    }