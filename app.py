
import os
from dotenv import load_dotenv
load_dotenv()   # must be FIRST



from flask import (
    Flask, render_template, request,
    redirect, url_for,
    session, flash
)
from flask_wtf import CSRFProtect

from config import Config
from models import db
SUPABASE_URL = os.environ.get("SUPABASE_URL")

# ---------------- APP INIT ----------------
app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["QR_FOLDER"], exist_ok=True)

csrf = CSRFProtect(app)


db.init_app(app)




from functools import wraps
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash, generate_password_hash
from utils.storage import delete_file

from utils.qr_generator import generate_upi_qr
from utils.receipt import generate_receipt
from utils.email_service import send_email

from models.user import User
from models.notice import Notice
from models.study_material import StudyMaterial
from models.announcement import Announcement
from models.paid_material import PaidMaterial
from models.payment import Payment
from models.faculty import Faculty
from utils.storage import upload_file
from utils.storage import get_public_url
from utils.storage import get_signed_url

from tempfile import NamedTemporaryFile


# ---------------- APP INIT ----------------
# ---------------- ADMIN BOOTSTRAP (LOCAL + RENDER SAFE) ----------------

def bootstrap_admin():
    # ❌ NEVER auto-run on Render / Production
    if os.environ.get("RENDER") == "true":
        return

    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        return

    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                name="Administrator",
                email=admin_email,
                role="admin",
                password=generate_password_hash(admin_password)
            )
            db.session.add(admin)
            db.session.commit()







# ---------------- BASE DIRECTORY ----------------


# ---------------- CREATE TABLES + ADMIN ----------------

# ---------------- FILE UPLOAD CONFIG ----------------




# ---------------- ADMIN DECORATOR ----------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def _file_ext(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _file_size_bytes(file_obj) -> int:
    stream = getattr(file_obj, "stream", file_obj)
    pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(pos)
    return size


def validate_upload(file_obj, allowed_exts: set[str], max_mb: int) -> tuple[bool, str | None]:
    if not file_obj or not file_obj.filename:
        return False, "File is required."

    ext = _file_ext(file_obj.filename)
    if ext not in allowed_exts:
        return False, f"Invalid file type. Allowed: {', '.join(sorted(allowed_exts))}."

    size = _file_size_bytes(file_obj)
    if size > max_mb * 1024 * 1024:
        return False, f"File too large. Max {max_mb}MB."

    return True, None


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(_error):
    flash("File too large. Please upload a smaller file.")
    return redirect(request.referrer or url_for("home"))

# ---------------- AUTH ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("home"))

        flash("Invalid credentials")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))
#---------------home---------------------
@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def home():
    # 🚑 CRITICAL: skip DB queries on Render startup/health scan
    if os.environ.get("RENDER") == "true":
        return render_template(
            "index.html",
            notices=[],
            announcements=[]
        )

    try:
        notices = Notice.query.order_by(
            Notice.created_at.desc()
        ).limit(5).all()

        announcements = Announcement.query.order_by(
            Announcement.created_at.desc()
        ).limit(1).all()

    except Exception as e:
        print(f"Error in home route: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        notices = []
        announcements = []

    return render_template(
        "index.html",
        notices=notices,
        announcements=announcements
    )

# ---------------- CONTACT ----------------
@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template(
        "admin_dashboard.html",
        notice_count=Notice.query.count(),
        announcement_count=Announcement.query.count(),
        material_count=StudyMaterial.query.count(),
        paid_material_count=PaidMaterial.query.count()
    )

# ---------------- ADMIN PAYMENT HISTORY ----------------
@app.route("/admin/payments")
@admin_required
def admin_payments():
    payments = db.session.query(
        Payment,
        PaidMaterial
    ).join(
        PaidMaterial,
        Payment.material_id == PaidMaterial.id
    ).order_by(
        Payment.created_at.desc()
    ).all()

    return render_template(
        "admin_payments.html",
        payments=payments
    )

# ---------------- NOTICES ----------------
@app.route("/notices", methods=["GET", "POST"])
def notices():
    if request.method == "POST":
        if session.get("role") != "admin":
            return redirect(url_for("login"))

        pdf = request.files.get("pdf")
        path = None

        if pdf and pdf.filename:
            ok, error = validate_upload(pdf, {"pdf"}, 10)
            if not ok:
                flash(error)
                return redirect(url_for("notices"))

            filename = secure_filename(pdf.filename)
            path = f"notices/{filename}"
            upload_file("notices", path, pdf)

        db.session.add(
            Notice(
                title=request.form["title"],
                content=request.form["content"],
                pdf_file=path
            )
        )
        db.session.commit()
        return redirect(url_for("notices"))

    return render_template(
        "notices.html",
        notices=Notice.query.order_by(Notice.created_at.desc()).all()
    )


# ---------------- DOWNLOAD NOTICE PDF ----------------
@app.route("/notices/pdf/<path:filepath>")
def download_notice_pdf(filepath):
    notice = Notice.query.filter_by(pdf_file=filepath).first_or_404()
    return redirect(get_public_url("notices", notice.pdf_file))


# ---------------- DELETE NOTICE ----------------
@app.route("/admin/notices/delete/<int:id>", methods=["POST"])
@admin_required
def delete_notice(id):
    notice = Notice.query.get_or_404(id)

    if notice.pdf_file:
        delete_file("notices", notice.pdf_file)

    db.session.delete(notice)
    db.session.commit()

    flash("Notice deleted successfully")
    return redirect(url_for("notices"))

# ---------------- ANNOUNCEMENTS ----------------
@app.route("/announcements", methods=["GET", "POST"])
def announcements():
    if request.method == "POST":
        if session.get("role") != "admin":
            return redirect(url_for("login"))

        file = request.files.get("file")
        path = None

        if file and file.filename:
            ok, error = validate_upload(file, {"pdf", "jpg", "jpeg", "png"}, 10)
            if not ok:
                flash(error)
                return redirect(url_for("announcements"))

            filename = secure_filename(file.filename)
            path = filename
            upload_file("announcements", path, file)

        db.session.add(
            Announcement(
                title=request.form["title"],
                content=request.form["content"],
                file_name=path   # ✅ FIXED
            )
        )
        db.session.commit()
        return redirect(url_for("announcements"))

    return render_template(
        "announcements.html",
        announcements=Announcement.query.order_by(
            Announcement.created_at.desc()
        ).all()
    )


# ---------------- DELETE ANNOUNCEMENT ----------------
@app.route("/admin/announcement/delete/<int:id>", methods=["POST"])
@admin_required
def delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)

    if announcement.file_name:
        delete_file("announcements", announcement.file_name)

    db.session.delete(announcement)
    db.session.commit()

    flash("Announcement deleted successfully")
    return redirect(url_for("announcements"))
# ---------------- DOWNLOAD ANNOUNCEMENT FILE ----------------
@app.route("/announcements/file/<path:filepath>")
def download_announcement_file(filepath):
    announcement = Announcement.query.filter_by(file_name=filepath).first_or_404()
    return redirect(
        get_public_url("announcements", announcement.file_name)
    )


# ---------------- STUDY MATERIALS ----------------
@app.route("/materials", methods=["GET", "POST"])
def materials():
    if request.method == "POST":
        if session.get("role") != "admin":
            return redirect(url_for("login"))

        file = request.files.get("file")
        if not file or not file.filename:
            return redirect(url_for("materials"))

        ok, error = validate_upload(file, {"pdf"}, 20)
        if not ok:
            flash(error)
            return redirect(url_for("materials"))

        ok, error = validate_upload(file, {"pdf"}, 20)
        if not ok:
            flash(error)
            return redirect(url_for("admin_paid_materials"))

        filename = secure_filename(file.filename)
        path = f"{request.form['class_name']}/{filename}"

        upload_file("study-materials", path, file)

        db.session.add(
            StudyMaterial(
                title=request.form["title"],
                subject=request.form["subject"],
                class_name=request.form["class_name"],
                file_name=path   # ✅ FIXED
            )
        )
        db.session.commit()
        return redirect(url_for("materials"))

    return render_template(
        "materials.html",
        materials=StudyMaterial.query.order_by(
            StudyMaterial.uploaded_at.desc()
        ).all()
    )


# ---------------- DOWNLOAD STUDY MATERIAL ----------------
@app.route("/study-material/<path:filepath>")
def download_study_material(filepath):
    material = StudyMaterial.query.filter_by(file_name=filepath).first_or_404()
    return redirect(
        get_public_url("study-materials", material.file_name)
    )


# ---------------- DELETE STUDY MATERIAL ----------------
@app.route("/admin/material/delete/<int:id>", methods=["POST"])
@admin_required
def delete_material(id):
    material = StudyMaterial.query.get_or_404(id)

    if material.file_name:
        delete_file("study-materials", material.file_name)

    db.session.delete(material)
    db.session.commit()

    flash("Study material deleted successfully")
    return redirect(url_for("materials"))


# ---------------- ADMIN PAID MATERIALS ----------------
@app.route("/admin/paid-materials", methods=["GET", "POST"])
@admin_required
def admin_paid_materials():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("PDF file is required")
            return redirect(url_for("admin_paid_materials"))

        filename = secure_filename(file.filename)
        path = f"{request.form['class_name']}/{filename}"

        upload_file("paid-materials", path, file)

        db.session.add(
            PaidMaterial(
                title=request.form["title"],
                class_name=request.form["class_name"],
                subject=request.form["subject"],
                price=float(request.form["price"]),
                file_name=path   # ✅ FIXED
            )
        )
        db.session.commit()

        flash("Paid material uploaded successfully")
        return redirect(url_for("admin_paid_materials"))

    return render_template(
        "admin_paid_materials.html",
        materials=PaidMaterial.query.order_by(
            PaidMaterial.created_at.desc()
        ).all()
    )


# ---------------- DELETE PAID MATERIAL ----------------
@app.route("/admin/paid-material/delete/<int:id>", methods=["POST"])
@admin_required
def delete_paid_material(id):
    material = PaidMaterial.query.get_or_404(id)

    if material.file_name:
        delete_file("paid-materials", material.file_name)

    db.session.delete(material)
    db.session.commit()

    flash("Paid material deleted successfully")
    return redirect(url_for("admin_paid_materials"))

#----------------faculty list----------------
@app.route("/faculty")
def faculty_public():
    principal = Faculty.query.filter_by(
        is_principal=True,
        is_active=True
    ).first()

    faculty_members = Faculty.query.filter_by(
        is_principal=False,
        is_active=True
    ).all()

    return render_template(
        "faculty.html",
        principal=principal,
        faculty_members=faculty_members
    )


@app.route("/admin/faculty", methods=["GET", "POST"])
@admin_required
def admin_faculty():
    if request.method == "POST":
        name = request.form["name"]
        designation = request.form["designation"]
        photo = request.files["photo"]

        ok, error = validate_upload(photo, {"jpg", "jpeg", "png"}, 5)
        if not ok:
            flash(error)
            return redirect(url_for("admin_faculty"))

        filename = secure_filename(photo.filename)
        path = f"faculty/{filename}"

        upload_file("faculty", path, photo)
        image_url = f"{SUPABASE_URL}/storage/v1/object/public/faculty/{path}"


        faculty = Faculty(
            name=name,
            designation=designation,
            image=image_url   # ✅ FIXED
        )
        db.session.add(faculty)
        db.session.commit()

        flash("Faculty added successfully")
        return redirect(url_for("admin_faculty"))

    faculty_members = Faculty.query.order_by(Faculty.created_at.desc()).all()
    return render_template(
        "admin_faculty.html",
        faculty_members=faculty_members
    )


@app.route("/admin/faculty/make-principal/<int:id>", methods=["POST"])
@admin_required
def make_principal(id):
    Faculty.query.filter_by(is_principal=True).update(
        {"is_principal": False}
    )

    faculty = Faculty.query.get_or_404(id)
    faculty.is_principal = True

    db.session.commit()
    flash(f"{faculty.name} is now the Principal")

    return redirect(url_for("admin_faculty"))


#-------delete faculty------------------
@app.route("/admin/faculty/delete/<int:id>", methods=["POST"])
@admin_required
def delete_faculty(id):
    faculty = Faculty.query.get_or_404(id)

    if faculty.image:
        delete_file("faculty", faculty.image)

    db.session.delete(faculty)
    db.session.commit()

    flash("Faculty deleted")
    return redirect(url_for("admin_faculty"))

# ---------------- PUBLIC PAID MATERIALS ----------------
@app.route("/paid-materials")
def paid_materials():
    selected_class = request.args.get("class")
    selected_subject = request.args.get("subject")

    query = PaidMaterial.query.filter_by(is_active=True)

    if selected_class:
        query = query.filter_by(class_name=selected_class)
    if selected_subject:
        query = query.filter_by(subject=selected_subject)

    materials = query.all()

    classes = [c[0] for c in db.session.query(PaidMaterial.class_name).distinct()]
    subjects = [s[0] for s in db.session.query(PaidMaterial.subject).distinct()]

    return render_template(
        "paid_materials.html",
        paid_materials=materials,
        classes=classes,
        subjects=subjects,
        selected_class=selected_class,
        selected_subject=selected_subject
    )

# ---------------- START PAYMENT ----------------
@app.route("/start-payment", methods=["POST"])
@csrf.exempt
def start_payment():
    material_id = request.form.get("material_id")
    email = request.form.get("email")

    if not material_id or not email:
        flash("Invalid request")
        return redirect(url_for("paid_materials"))

    if not email.endswith("@gmail.com"):
        flash("Please enter a valid Gmail address")
        return redirect(url_for("paid_materials"))

    material = PaidMaterial.query.filter_by(
        id=material_id,
        is_active=True
    ).first()

    if not material:
        flash("Material not found")
        return redirect(url_for("paid_materials"))

    session["payment_material_id"] = material.id
    session["payment_email"] = email
    session["payment_amount"] = material.price

    return redirect(url_for("payment_page"))

# ---------------- PAYMENT PAGE ----------------
@app.route("/payment")
def payment_page():
    material_id = session.get("payment_material_id")
    email = session.get("payment_email")

    if not material_id:
        return redirect(url_for("paid_materials"))

    material = PaidMaterial.query.get_or_404(material_id)

    upi_id = os.environ.get("UPI_ID")
    upi_name = os.environ.get("UPI_NAME")

    upi_link = (
        f"upi://pay?"
        f"pa={upi_id}"
        f"&pn={upi_name.replace(' ', '%20')}"
        f"&am={material.price}"
        f"&cu=INR"
        f"&tn=Paid%20Study%20Material"
    )

    # ---------- QR GENERATION ----------
    qr_filename = f"upi_qr_{material.id}_{material.price}.png"
    qr_path = os.path.join(app.config["QR_FOLDER"], qr_filename)

# Generate QR only if not already present
    if not os.path.exists(qr_path):
        generate_upi_qr(upi_link, qr_path)

    return render_template(
        "payment.html",
        material=material,
        amount=material.price,
        email=email,
        upi_id=upi_id,
    upi_name=upi_name,
        upi_link=upi_link,
        qr_image=qr_filename
     )
    

# ---------------- SUBMIT PAYMENT ----------------
@app.route("/submit-payment", methods=["POST"])
@csrf.exempt
def submit_payment():
    email = request.form.get("email")
    material_id = request.form.get("material_id")
    utr = request.form.get("utr")
    

    # -------- BASIC VALIDATION --------
    if not email or not material_id or not utr:
        flash("Invalid submission.")
        return redirect(url_for("paid_materials"))

    if len(utr.strip()) < 8:
        flash("Invalid UTR / Transaction ID.")
        return redirect(url_for("paid_materials"))

    material = PaidMaterial.query.get_or_404(material_id)

    # -------- RATE LIMIT (24 HOURS / SAME MATERIAL) --------
    last_payment = Payment.query.filter_by(
        email=email,
        material_id=material.id
    ).order_by(Payment.created_at.desc()).first()

    if last_payment and datetime.utcnow() - last_payment.created_at < timedelta(hours=24):
        # Resend email + receipt instead of blocking silently
        download_link = url_for(
            "download_paid_material",
            token=last_payment.download_token,
            _external=True
        )

        receipt_tmp_path = None
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            generate_receipt(
                receipt_path=tmp.name,
                school_name=os.environ.get("SCHOOL_NAME", "School"),
                email=email,
                material=material,
                amount=last_payment.amount,
                utr=last_payment.utr
            )
            receipt_tmp_path = tmp.name

        email_sent = False
        try:
            send_email(
                to_email=email,
                subject="Your Study Material & Receipt",
                body=f"""
            Thank you for your payment.

            Download your study material here:
            {download_link}

            This link is valid for 24 hours.
            """,
                attachments=[receipt_tmp_path]
            )
            email_sent = True
        except Exception as exc:
            app.logger.exception("Email resend failed: %s", exc)
        finally:
            if receipt_tmp_path and os.path.exists(receipt_tmp_path):
                os.remove(receipt_tmp_path)

        if email_sent:
            flash("You already purchased this material. We resent your PDF and receipt.", "success")
        else:
            flash("You already purchased this material, but email failed to send.", "error")

        return redirect(url_for("home"))

    # -------- 🚨 BLOCK REUSED UTR (GLOBAL) --------
    existing_utr = Payment.query.filter_by(utr=utr.strip()).first()
    if existing_utr:
        flash("This UTR / Transaction ID has already been used.")
        return redirect(url_for("paid_materials"))

    # -------- SAVE PAYMENT --------
    payment = Payment(
        material_id=material.id,
        email=email,
        amount=material.price,
        utr=utr.strip()
    )
    db.session.add(payment)
    db.session.commit()

    # -------- RECEIPT --------
  
    download_link = url_for(
    "download_paid_material",
    token=payment.download_token,
    _external=True
)

    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        generate_receipt(
           receipt_path=tmp.name,
           school_name=os.environ.get("SCHOOL_NAME", "School"),
           email=email,
           material=material,
           amount=material.price,
           utr=utr.strip()
        )
        receipt_tmp_path = tmp.name

    # upload to Supabase
    receipt_supabase_path = f"receipts/receipt_{payment.id}.pdf"
    with open(receipt_tmp_path, "rb") as f:
       receipt_supabase_path = f"receipt_{payment.id}.pdf"
       upload_file("receipts", receipt_supabase_path, f)

    # send email
    email_sent = False
    try:
        send_email(
            to_email=email,
            subject="Your Study Material & Receipt",
            body=f"""
        Thank you for your payment.

        Download your study material here:
        {download_link}

        This link is valid for 24 hours.
        """,
            attachments=[receipt_tmp_path]
        )
        email_sent = True
    except Exception as exc:
        app.logger.exception("Email send failed: %s", exc)
    finally:
        if receipt_tmp_path and os.path.exists(receipt_tmp_path):
            os.remove(receipt_tmp_path)

    if email_sent:
        flash("Payment successful! PDF and receipt sent to your email.", "success")
    else:
        flash("Payment saved, but email failed to send. Please contact support.", "error")

    return redirect(url_for("home"))

# ---------------- DOWNLOAD PAID MATERIAL ----------------

@app.route("/download/<token>")
def download_paid_material(token):
    payment = Payment.query.filter_by(download_token=token).first_or_404()

    if datetime.utcnow() - payment.created_at > timedelta(hours=24):
        flash("Download link expired.")
        return redirect(url_for("home"))

    material = PaidMaterial.query.get_or_404(payment.material_id)

    signed_url = get_signed_url(
        bucket="paid-materials",
         path=material.file_name,
        expires_in=60 * 60  # 1 hour
    )

    return redirect(signed_url)

# ---------------- SERVE UPI QR IMAGE ----------------
@app.route("/upi-qr/<filename>")
def download_qr(filename):
    return redirect(
        get_public_url("qr-codes", filename)
    )



# ---------------- RUN ----------------
if __name__ == "__main__":
    bootstrap_admin()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")


