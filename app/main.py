
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
)


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(
    bind=engine
)


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

    sentence_count = (
        db.query(Sentence).count()
    )


    # --------------------------------------------------------
    # Check minimum sentences
    # --------------------------------------------------------

    if sentence_count < 20:

        return templates.TemplateResponse(

            request=request,

            name="index.html",

            context={

                "sentences": [],

                "participant_id": "",

                "error": (

                    "Form haijawa tayari. "

                    f"Database ina sentensi "
                    f"{sentence_count}. "

                    "Inahitajika angalau "
                    "sentensi 20."

                ),

            },

        )


    # --------------------------------------------------------
    # Get sentence IDs
    # --------------------------------------------------------

    sentence_ids = [

        row[0]

        for row in db.query(
            Sentence.id
        ).all()

    ]


    # --------------------------------------------------------
    # Choose random 20
    # --------------------------------------------------------

    selected_ids = random.sample(

        sentence_ids,

        20

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
    # Participant ID
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

    sentence_count = (

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

            "response_count":
                response_count,

            "responses":
                responses,

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