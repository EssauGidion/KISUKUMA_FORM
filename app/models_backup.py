# ============================================================
# MODELS.PY
# Database models
# ============================================================

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from .database import Base


# ============================================================
# SENTENCE MODEL
# ============================================================

class Sentence(Base):

    __tablename__ = "sentences"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    kiswahili = Column(
        Text,
        nullable=False
    )


# ============================================================
# RESPONSE MODEL
# ============================================================

class Response(Base):

    __tablename__ = "responses"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    kiswahili = Column(
        Text,
        nullable=False
    )

    kisukuma = Column(
        Text,
        nullable=False
    )

    participant_id = Column(
        String(100),
        nullable=False,
        index=True
    )


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Kisukuma Translation Form",
    description=(
        "Kiswahili to Kisukuma "
        "data collection system"
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
# HOME
# ============================================================

@app.get("/")
def home():
    """
    Homepage inampeleka user kwenye form.
    """

    return RedirectResponse(
        url="/form"
    )


# ============================================================
# SHOW FORM
# ============================================================

@app.get("/form")
def show_form(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Inaonyesha sentensi 20 random
    kutoka kwenye database.
    """

    # --------------------------------------------------------
    # Count sentences
    # --------------------------------------------------------

    sentence_count = (
        db.query(Sentence).count()
    )

    # --------------------------------------------------------
    # Check if enough sentences exist
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
    # Get all sentence IDs
    # --------------------------------------------------------

    sentence_ids = [
        row[0]
        for row in db.query(
            Sentence.id
        ).all()
    ]

    # --------------------------------------------------------
    # Select 20 random IDs
    # --------------------------------------------------------

    selected_ids = random.sample(
        sentence_ids,
        20
    )

    # --------------------------------------------------------
    # Get selected sentences
    # --------------------------------------------------------

    sentences = (
        db.query(Sentence)
        .filter(
            Sentence.id.in_(selected_ids)
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
    # Show form
    # --------------------------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "sentences": sentences,
            "participant_id": participant_id,
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
    """
    Inapokea majibu ya Kisukuma
    na kuya-save kwenye database.
    """

    # --------------------------------------------------------
    # Get form data
    # --------------------------------------------------------

    form_data = await request.form()

    # --------------------------------------------------------
    # Participant ID
    # --------------------------------------------------------

    participant_id = form_data.get(
        "participant_id"
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
    # Loop through form fields
    # --------------------------------------------------------

    for key, value in form_data.items():

        # We only need question fields
        if not key.startswith(
            "question_"
        ):
            continue

        # ----------------------------------------------------
        # Get sentence ID
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
        # Get Kisukuma answer
        # ----------------------------------------------------

        kisukuma_answer = str(
            value
        ).strip()

        # Skip empty answer
        if not kisukuma_answer:
            continue

        # ----------------------------------------------------
        # Find sentence
        # ----------------------------------------------------

        sentence = (
            db.query(Sentence)
            .filter(
                Sentence.id == sentence_id
            )
            .first()
        )

        if not sentence:
            continue

        # ----------------------------------------------------
        # Create response
        # ----------------------------------------------------

        response = Response(
            kiswahili=sentence.kiswahili,
            kisukuma=kisukuma_answer,
            participant_id=participant_id,
        )

        db.add(response)

        saved += 1

    # --------------------------------------------------------
    # Save database
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
    """
    Admin dashboard.
    """

    # --------------------------------------------------------
    # Count sentences
    # --------------------------------------------------------

    sentence_count = (
        db.query(Sentence).count()
    )

    # --------------------------------------------------------
    # Count responses
    # --------------------------------------------------------

    response_count = (
        db.query(Response).count()
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
    # Show dashboard
    # --------------------------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "sentence_count": sentence_count,
            "response_count": response_count,
            "responses": responses,
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
    """
    Admin ana-upload CSV yenye
    sentensi za Kiswahili.
    """

    # --------------------------------------------------------
    # Check filename
    # --------------------------------------------------------

    if not file.filename:

        return {
            "error": (
                "Tafadhali chagua CSV file."
            )
        }

    # --------------------------------------------------------
    # Check extension
    # --------------------------------------------------------

    if not file.filename.lower().endswith(
        ".csv"
    ):

        return {
            "error": (
                "File lazima iwe CSV."
            )
        }

    try:

        # ----------------------------------------------------
        # Read uploaded file
        # ----------------------------------------------------

        contents = await file.read()

        # ----------------------------------------------------
        # Read CSV
        # ----------------------------------------------------

        df = pd.read_csv(
            io.BytesIO(contents)
        )

        # ----------------------------------------------------
        # Clean column names
        # ----------------------------------------------------

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        # ----------------------------------------------------
        # Possible Kiswahili columns
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
        # Column not found
        # ----------------------------------------------------

        if selected_column is None:

            return {
                "error": (
                    "CSV yako haina column "
                    "inayotambulika ya Kiswahili."
                ),
                "available_columns": (
                    df.columns.tolist()
                ),
            }

        # ----------------------------------------------------
        # Keep Kiswahili column
        # ----------------------------------------------------

        df = df[
            [selected_column]
        ].copy()

        df.columns = [
            "kiswahili"
        ]

        # ----------------------------------------------------
        # Clean values
        # ----------------------------------------------------

        df["kiswahili"] = (
            df["kiswahili"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # Remove empty sentences
        df = df[
            df["kiswahili"] != ""
        ]

        # Remove duplicates
        df = df.drop_duplicates(
            subset=["kiswahili"]
        )

        # ----------------------------------------------------
        # Insert database
        # ----------------------------------------------------

        records = df.to_dict(
            orient="records"
        )

        batch_size = 5000

        for start in range(
            0,
            len(records),
            batch_size,
        ):

            batch = records[
                start:start + batch_size
            ]

            db.bulk_insert_mappings(
                Sentence,
                batch,
            )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        db.commit()

        # ----------------------------------------------------
        # Redirect admin
        # ----------------------------------------------------

        return RedirectResponse(
            url="/admin",
            status_code=303,
        )

    except Exception as e:

        db.rollback()

        return {
            "error": (
                "Kuna tatizo wakati wa "
                "ku-import CSV."
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
    """
    Ina-import:

    dataset/sentences.csv
    """

    # --------------------------------------------------------
    # CSV path
    # --------------------------------------------------------

    csv_path = os.path.join(
        "dataset",
        "sentences.csv",
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
        # Clean column names
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
        # Column not found
        # ----------------------------------------------------

        if selected_column is None:

            return {
                "error": (
                    "Column ya Kiswahili "
                    "haijapatikana."
                ),
                "available_columns": (
                    df.columns.tolist()
                ),
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
        # Clean values
        # ----------------------------------------------------

        df["kiswahili"] = (
            df["kiswahili"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # Remove empty
        df = df[
            df["kiswahili"] != ""
        ]

        # Remove duplicates
        df = df.drop_duplicates(
            subset=["kiswahili"]
        )

        # ----------------------------------------------------
        # Convert records
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
            batch_size,
        ):

            batch = records[
                start:start + batch_size
            ]

            db.bulk_insert_mappings(
                Sentence,
                batch,
            )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        db.commit()

        # ----------------------------------------------------
        # Count
        # ----------------------------------------------------

        total = (
            db.query(Sentence).count()
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
                "Kuna tatizo wakati wa "
                "ku-import CSV."
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
    """
    Download collected dataset
    as CSV.
    """

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

        data.append(
            {
                "id": response.id,
                "kiswahili": (
                    response.kiswahili
                ),
                "kisukuma": (
                    response.kisukuma
                ),
                "participant_id": (
                    response.participant_id
                ),
            }
        )

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
    # Bytes
    # --------------------------------------------------------

    csv_bytes = (
        output
        .getvalue()
        .encode("utf-8-sig")
    )

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    return StreamingResponse(
        io.BytesIO(csv_bytes),
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
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    """
    Kuangalia kama API iko hai.
    """

    return {
        "status": "ok",
        "message": (
            "Kisukuma Form API "
            "inafanya kazi."
        ),
    }