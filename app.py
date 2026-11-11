
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

import sqlite3
import os
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

app = Flask(__name__)

app.secret_key = "ProSchool_faculty_portal_secret_key"

DATABASE = os.path.join(app.root_path, "ProSchool.db")

FACULTY_EMAIL = "faculty@ProSchool.edu"
FACULTY_PASSWORD = "faculty123"


# ==========================================
# SCHOOL STANDARDS
# ==========================================

SCHOOL_CLASSES = [
    "1st Std",
    "2nd Std",
    "3rd Std",
    "4th Std",
    "5th Std",
    "6th Std",
    "7th Std",
    "8th Std",
    "9th Std",
    "10th Std",
    "11th Std - Bio-Maths",
    "11th Std - Computer Science",
    "11th Std - Arts",
    "12th Std - Bio-Maths",
    "12th Std - Computer Science",
    "12th Std - Arts"
]


# ==========================================
# SCHOOL SUBJECTS
# ==========================================

SCHOOL_SUBJECTS = [
    "Tamil",
    "English",
    "Mathematics",
    "Science",
    "Social Science",
    "Physics",
    "Chemistry",
    "Biology",
    "Computer Science",
    "Economics",
    "Accountancy",
    "Commerce",
    "History",
    "Geography"
]


# ==========================================
# EXAMINATION TYPES
# ==========================================

EXAM_TYPES = [
    "Unit Test 1",
    "Unit Test 2",
    "Quarterly Examination",
    "Half-Yearly Examination",
    "Unit Test 3",
    "Unit Test 4",
    "Annual Examination"
]
WEEK_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday"
]

# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    # Enable foreign key relationships
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==========================================
# CREATE DATABASE TABLES
# ==========================================

def init_db():

    connection = get_db_connection()

    # STUDENT TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            roll_number TEXT NOT NULL UNIQUE,

            name TEXT NOT NULL,

            class_name TEXT NOT NULL,

            email TEXT,

            phone TEXT
        )
    """)

    # ATTENDANCE TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER NOT NULL,

            attendance_date TEXT NOT NULL,

            status TEXT NOT NULL
                CHECK(status IN ('Present', 'Absent')),

            UNIQUE(student_id, attendance_date),

            FOREIGN KEY(student_id)
                REFERENCES students(id)
                ON DELETE CASCADE
        )
    """)

    # MARKS AND EXAMINATION RESULTS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS marks (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER NOT NULL,

            subject TEXT NOT NULL,

            exam_name TEXT NOT NULL,

            exam_date TEXT NOT NULL,

            max_marks REAL NOT NULL,

            marks_obtained REAL NOT NULL,

            UNIQUE(
                student_id,
                subject,
                exam_name,
                exam_date
            ),

            FOREIGN KEY(student_id)
                REFERENCES students(id)
                ON DELETE CASCADE
        )
    """)


    # SUBJECTS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            faculty_email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(subject_name, class_name, faculty_email)
        )
    """)

    # TIMETABLE TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            period_number INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            room TEXT,
            faculty_email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                class_name,
                day_of_week,
                period_number,
                faculty_email
            )
        )
    """)

    # ANNOUNCEMENTS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            target_class TEXT NOT NULL DEFAULT 'All School',
            faculty_email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FACULTY PROFILES TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS faculty_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_email TEXT NOT NULL UNIQUE,
            faculty_name TEXT NOT NULL DEFAULT 'Faculty Member',
            faculty_id TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            qualification TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FACULTY ACCOUNTS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS faculty_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_name TEXT NOT NULL,
            faculty_email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # CREATE THE EXISTING DEMO FACULTY ACCOUNT
    existing_account = connection.execute("""
        SELECT id FROM faculty_accounts
        WHERE faculty_email = ?
    """, (FACULTY_EMAIL,)).fetchone()

    if existing_account is None:

        connection.execute("""
            INSERT INTO faculty_accounts (
                faculty_name,
                faculty_email,
                password_hash
            )
            VALUES (?, ?, ?)
        """, (
            "Faculty Member",
            FACULTY_EMAIL,
            generate_password_hash(FACULTY_PASSWORD)
        ))
    connection.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            work_type TEXT NOT NULL,
            description TEXT NOT NULL,
            class_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            due_date TEXT NOT NULL,
            max_marks REAL NOT NULL DEFAULT 0,
            faculty_email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()

    connection.close()


# ==========================================
# LOGIN PAGE
# ==========================================

@app.route("/")
def home():

    if "faculty" in session:

        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ==========================================
# FACULTY LOGIN
# ==========================================


@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    connection = get_db_connection()

    account = connection.execute("""
        SELECT *
        FROM faculty_accounts
        WHERE faculty_email = ?
    """, (email,)).fetchone()

    connection.close()

    if account and check_password_hash(
        account["password_hash"], password
    ):

        session.clear()
        session["faculty"] = email

        # Create a personal profile if one does not exist
        connection = get_db_connection()

        connection.execute("""
            INSERT OR IGNORE INTO faculty_profiles (
                faculty_email,
                faculty_name,
                faculty_id,
                department
            )
            VALUES (?, ?, ?, ?)
        """, (
            email,
            account["faculty_name"],
            f"FAC-{account['id']:03d}",
            "School Faculty"
        ))

        connection.commit()
        connection.close()

        return redirect(url_for("dashboard"))

    return render_template(
        "login.html",
        error="Invalid email or password."
    )


# ==========================================
# FACULTY DASHBOARD
# ==========================================

# ==========================================
# FACULTY DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "faculty" not in session:
        return redirect(url_for("home"))

    connection = get_db_connection()

    # Total registered students
    total_students = connection.execute("""
        SELECT COUNT(*) FROM students
    """).fetchone()[0]

    # Number of standards containing students
    total_classes = connection.execute("""
        SELECT COUNT(DISTINCT class_name)
        FROM students
    """).fetchone()[0]

    # Subjects assigned to this faculty
    total_subjects = connection.execute("""
        SELECT COUNT(*)
        FROM subjects
        WHERE faculty_email = ?
    """, (session["faculty"],)).fetchone()[0]

    # Total saved examination marks
    total_marks_records = connection.execute("""
        SELECT COUNT(*)
        FROM marks
        JOIN students ON marks.student_id = students.id
    """).fetchone()[0]

    # Attendance statistics
    attendance_total = connection.execute("""
        SELECT COUNT(*) FROM attendance
    """).fetchone()[0]

    attendance_present = connection.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE status = 'Present'
    """).fetchone()[0]

    average_attendance = (
        round(attendance_present / attendance_total * 100, 1)
        if attendance_total > 0
        else 0
    )

    connection.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_classes=total_classes,
        total_subjects=total_subjects,
        total_marks_records=total_marks_records,
        average_attendance=average_attendance,
        faculty_email=session["faculty"]
    )


# ==========================================
# STUDENT MANAGEMENT - VIEW AND SEARCH
# ==========================================

@app.route("/students")
def students():

    if "faculty" not in session:

        return redirect(url_for("home"))

    search = request.args.get("q", "").strip()

    connection = get_db_connection()

    if search:

        students_list = connection.execute("""
            SELECT *
            FROM students

            WHERE name LIKE ?
               OR roll_number LIKE ?
               OR class_name LIKE ?

            ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()

    else:

        students_list = connection.execute("""
            SELECT *
            FROM students
            ORDER BY id DESC
        """).fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=students_list,
        search=search,
        school_classes=SCHOOL_CLASSES
    )


# ==========================================
# ADD NEW STUDENT
# ==========================================

@app.route("/students/add", methods=["POST"])
def add_student():

    if "faculty" not in session:

        return redirect(url_for("home"))

    name = request.form.get("name", "").strip()

    roll_number = request.form.get(
        "roll_number", ""
    ).strip()

    class_name = request.form.get(
        "class_name", ""
    ).strip()

    email = request.form.get("email", "").strip()

    phone = request.form.get("phone", "").strip()

    if not name or not roll_number or not class_name:

        flash(
            "Please complete all required fields.",
            "error"
        )

        return redirect(url_for("students"))

    if class_name not in SCHOOL_CLASSES:

        flash(
            "Please select a valid school standard.",
            "error"
        )

        return redirect(url_for("students"))

    connection = get_db_connection()

    try:

        connection.execute("""
            INSERT INTO students (
                name,
                roll_number,
                class_name,
                email,
                phone
            )

            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            roll_number,
            class_name,
            email,
            phone
        ))

        connection.commit()

        flash(
            "Student added successfully!",
            "success"
        )

    except sqlite3.IntegrityError:

        flash(
            "This admission or roll number already exists.",
            "error"
        )

    finally:

        connection.close()

    return redirect(url_for("students"))


# ==========================================
# EDIT STUDENT DETAILS
# ==========================================

@app.route(
    "/students/edit/<int:student_id>",
    methods=["GET", "POST"]
)
def edit_student(student_id):

    if "faculty" not in session:

        return redirect(url_for("home"))

    connection = get_db_connection()

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        roll_number = request.form.get(
            "roll_number", ""
        ).strip()

        class_name = request.form.get(
            "class_name", ""
        ).strip()

        email = request.form.get("email", "").strip()

        phone = request.form.get("phone", "").strip()

        if not name or not roll_number or not class_name:

            flash(
                "Please complete all required fields.",
                "error"
            )

        elif class_name not in SCHOOL_CLASSES:

            flash(
                "Please select a valid school standard.",
                "error"
            )

        else:

            try:

                connection.execute("""
                    UPDATE students

                    SET
                        name = ?,
                        roll_number = ?,
                        class_name = ?,
                        email = ?,
                        phone = ?

                    WHERE id = ?
                """, (
                    name,
                    roll_number,
                    class_name,
                    email,
                    phone,
                    student_id
                ))

                connection.commit()

                connection.close()

                flash(
                    "Student updated successfully!",
                    "success"
                )

                return redirect(url_for("students"))

            except sqlite3.IntegrityError:

                flash(
                    "This admission number is already in use.",
                    "error"
                )

    student = connection.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()

    connection.close()

    if student is None:

        flash(
            "Student record not found.",
            "error"
        )

        return redirect(url_for("students"))

    return render_template(
        "edit_student.html",
        student=student,
        school_classes=SCHOOL_CLASSES
    )


# ==========================================
# DELETE STUDENT
# ==========================================

@app.route(
    "/students/delete/<int:student_id>",
    methods=["POST"]
)
def delete_student(student_id):

    if "faculty" not in session:

        return redirect(url_for("home"))

    connection = get_db_connection()

    connection.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (student_id,))

    connection.commit()

    connection.close()

    flash(
        "Student deleted successfully.",
        "success"
    )

    return redirect(url_for("students"))


# ==========================================
# ATTENDANCE MANAGEMENT PAGE
# ==========================================

@app.route("/attendance")
def attendance():

    if "faculty" not in session:

        return redirect(url_for("home"))

    selected_class = request.args.get(
        "class_name",
        SCHOOL_CLASSES[0]
    ).strip()

    attendance_date = request.args.get(
        "attendance_date",
        date.today().isoformat()
    ).strip()

    # Validate standard
    if selected_class not in SCHOOL_CLASSES:

        selected_class = SCHOOL_CLASSES[0]

    # Validate date
    try:

        datetime.strptime(
            attendance_date,
            "%Y-%m-%d"
        )

    except ValueError:

        attendance_date = date.today().isoformat()

    connection = get_db_connection()

    students_list = connection.execute("""
        SELECT

            students.id,
            students.name,
            students.roll_number,
            students.class_name,

            attendance.status

        FROM students

        LEFT JOIN attendance

            ON students.id = attendance.student_id

            AND attendance.attendance_date = ?

        WHERE students.class_name = ?

        ORDER BY students.name

    """, (
        attendance_date,
        selected_class
    )).fetchall()

    connection.close()

    present_count = sum(
        1 for student in students_list
        if student["status"] == "Present"
    )

    absent_count = sum(
        1 for student in students_list
        if student["status"] == "Absent"
    )

    total_students = len(students_list)

    unmarked_count = (
        total_students
        - present_count
        - absent_count
    )

    return render_template(
        "attendance.html",

        students=students_list,

        school_classes=SCHOOL_CLASSES,

        selected_class=selected_class,

        attendance_date=attendance_date,

        present_count=present_count,

        absent_count=absent_count,

        unmarked_count=unmarked_count,

        total_students=total_students
    )


# ==========================================
# SAVE ATTENDANCE
# ==========================================

@app.route(
    "/attendance/save",
    methods=["POST"]
)
def save_attendance():

    if "faculty" not in session:

        return redirect(url_for("home"))

    selected_class = request.form.get(
        "class_name", ""
    ).strip()

    attendance_date = request.form.get(
        "attendance_date", ""
    ).strip()

    if selected_class not in SCHOOL_CLASSES:

        flash(
            "Please select a valid school standard.",
            "error"
        )

        return redirect(url_for("attendance"))

    try:

        datetime.strptime(
            attendance_date,
            "%Y-%m-%d"
        )

    except ValueError:

        flash(
            "Please select a valid attendance date.",
            "error"
        )

        return redirect(url_for("attendance"))

    connection = get_db_connection()

    students_list = connection.execute("""
        SELECT id
        FROM students
        WHERE class_name = ?
    """, (selected_class,)).fetchall()

    if not students_list:

        connection.close()

        flash(
            "There are no students in this standard yet.",
            "error"
        )

        return redirect(url_for(
            "attendance",
            class_name=selected_class,
            attendance_date=attendance_date
        ))

    attendance_records = []

    # Check each student's attendance
    for student in students_list:

        status = request.form.get(
            f"status_{student['id']}",
            ""
        )

        if status not in ["Present", "Absent"]:

            connection.close()

            flash(
                "Please mark every student Present or Absent.",
                "error"
            )

            return redirect(url_for(
                "attendance",
                class_name=selected_class,
                attendance_date=attendance_date
            ))

        attendance_records.append((
            student["id"],
            attendance_date,
            status
        ))

    # Insert new records or update existing records
    connection.executemany("""
        INSERT INTO attendance (
            student_id,
            attendance_date,
            status
        )

        VALUES (?, ?, ?)

        ON CONFLICT(student_id, attendance_date)

        DO UPDATE SET
            status = excluded.status

    """, attendance_records)

    connection.commit()

    connection.close()

    flash(
        "Attendance saved successfully!",
        "success"
    )

    return redirect(url_for(
        "attendance",
        class_name=selected_class,
        attendance_date=attendance_date
    ))


# ==========================================
# MARKS MANAGEMENT PAGE
# ==========================================

@app.route("/marks")
def marks():

    if "faculty" not in session:

        return redirect(url_for("home"))

    selected_class = request.args.get(
        "class_name",
        SCHOOL_CLASSES[0]
    ).strip()

    subject = request.args.get(
        "subject",
        SCHOOL_SUBJECTS[0]
    ).strip()

    exam_name = request.args.get(
        "exam_name",
        EXAM_TYPES[0]
    ).strip()

    exam_date = request.args.get(
        "exam_date",
        date.today().isoformat()
    ).strip()

    max_marks = request.args.get(
        "max_marks",
        "100"
    ).strip()

    # Validate selected standard
    if selected_class not in SCHOOL_CLASSES:

        selected_class = SCHOOL_CLASSES[0]

    # Validate subject
    if subject not in SCHOOL_SUBJECTS:

        subject = SCHOOL_SUBJECTS[0]

    # Validate examination
    if exam_name not in EXAM_TYPES:

        exam_name = EXAM_TYPES[0]

    # Validate examination date
    try:

        datetime.strptime(
            exam_date,
            "%Y-%m-%d"
        )

    except ValueError:

        exam_date = date.today().isoformat()

    # Validate maximum marks
    try:

        max_marks_value = float(max_marks)

        if not 0 < max_marks_value <= 1000:

            raise ValueError

    except ValueError:

        max_marks_value = 100.0

    connection = get_db_connection()

    students_list = connection.execute("""
        SELECT

            students.id,
            students.name,
            students.roll_number,
            students.class_name,

            marks.marks_obtained,
            marks.max_marks

        FROM students

        LEFT JOIN marks

            ON students.id = marks.student_id

            AND marks.subject = ?

            AND marks.exam_name = ?

            AND marks.exam_date = ?

        WHERE students.class_name = ?

        ORDER BY students.name

    """, (
        subject,
        exam_name,
        exam_date,
        selected_class
    )).fetchall()

    connection.close()

    total_students = len(students_list)

    entered_marks = [
        student for student in students_list
        if student["marks_obtained"] is not None
    ]

    completed_count = len(entered_marks)

    pending_count = (
        total_students - completed_count
    )

    average_marks = 0

    if completed_count:

        average_marks = round(
            sum(
                student["marks_obtained"]
                / student["max_marks"] * 100

                for student in entered_marks
            ) / completed_count,
            2
        )

    return render_template(
        "marks.html",

        students=students_list,

        school_classes=SCHOOL_CLASSES,

        subjects=SCHOOL_SUBJECTS,

        exam_types=EXAM_TYPES,

        selected_class=selected_class,

        selected_subject=subject,

        exam_name=exam_name,

        exam_date=exam_date,

        max_marks=max_marks_value,

        total_students=total_students,

        completed_count=completed_count,

        pending_count=pending_count,

        average_marks=average_marks
    )


# ==========================================
# SAVE AND UPDATE EXAMINATION MARKS
# ==========================================

@app.route(
    "/marks/save",
    methods=["POST"]
)
def save_marks():

    if "faculty" not in session:

        return redirect(url_for("home"))

    selected_class = request.form.get(
        "class_name", ""
    ).strip()

    subject = request.form.get(
        "subject", ""
    ).strip()

    exam_name = request.form.get(
        "exam_name", ""
    ).strip()

    exam_date = request.form.get(
        "exam_date", ""
    ).strip()

    # Validate maximum marks
    try:

        max_marks = float(
            request.form.get(
                "max_marks",
                "100"
            )
        )

        if not 0 < max_marks <= 1000:

            raise ValueError

    except ValueError:

        flash(
            "Please enter valid maximum marks.",
            "error"
        )

        return redirect(url_for("marks"))

    # Validate school standard
    if selected_class not in SCHOOL_CLASSES:

        flash(
            "Invalid school standard.",
            "error"
        )

        return redirect(url_for("marks"))

    # Validate subject
    if subject not in SCHOOL_SUBJECTS:

        flash(
            "Please select a valid subject.",
            "error"
        )

        return redirect(url_for("marks"))

    # Validate examination
    if exam_name not in EXAM_TYPES:

        flash(
            "Please select a valid examination.",
            "error"
        )

        return redirect(url_for("marks"))

    # Validate examination date
    try:

        datetime.strptime(
            exam_date,
            "%Y-%m-%d"
        )

    except ValueError:

        flash(
            "Please select a valid examination date.",
            "error"
        )

        return redirect(url_for("marks"))

    connection = get_db_connection()

    students_list = connection.execute("""
        SELECT id
        FROM students
        WHERE class_name = ?
    """, (selected_class,)).fetchall()

    if not students_list:

        connection.close()

        flash(
            "No students found in this standard.",
            "error"
        )

        return redirect(url_for(
            "marks",
            class_name=selected_class,
            subject=subject,
            exam_name=exam_name,
            exam_date=exam_date,
            max_marks=max_marks
        ))

    records = []

    # Validate each student's marks
    for student in students_list:

        raw_marks = request.form.get(
            f"marks_{student['id']}",
            ""
        ).strip()

        if raw_marks == "":

            connection.close()

            flash(
                "Please enter marks for every student before saving.",
                "error"
            )

            return redirect(url_for(
                "marks",
                class_name=selected_class,
                subject=subject,
                exam_name=exam_name,
                exam_date=exam_date,
                max_marks=max_marks
            ))

        try:

            obtained = float(raw_marks)

            if not 0 <= obtained <= max_marks:

                raise ValueError

        except ValueError:

            connection.close()

            flash(
                "Marks must be between 0 and maximum marks.",
                "error"
            )

            return redirect(url_for(
                "marks",
                class_name=selected_class,
                subject=subject,
                exam_name=exam_name,
                exam_date=exam_date,
                max_marks=max_marks
            ))

        records.append((
            student["id"],
            subject,
            exam_name,
            exam_date,
            max_marks,
            obtained
        ))

    # Insert or update the marks
    connection.executemany("""
        INSERT INTO marks (
            student_id,
            subject,
            exam_name,
            exam_date,
            max_marks,
            marks_obtained
        )

        VALUES (?, ?, ?, ?, ?, ?)

        ON CONFLICT(
            student_id,
            subject,
            exam_name,
            exam_date
        )

        DO UPDATE SET

            max_marks = excluded.max_marks,

            marks_obtained = excluded.marks_obtained

    """, records)

    connection.commit()

    connection.close()

    flash(
        "Examination marks saved successfully!",
        "success"
    )

    return redirect(url_for(
        "marks",
        class_name=selected_class,
        subject=subject,
        exam_name=exam_name,
        exam_date=exam_date,
        max_marks=max_marks
    ))


# ==========================================
# SUBJECT MANAGEMENT
# ==========================================

@app.route("/subjects")
def subjects():

    if "faculty" not in session:
        return redirect(url_for("home"))

    connection = get_db_connection()

    subjects_list = connection.execute("""
        SELECT *
        FROM subjects
        WHERE faculty_email = ?
        ORDER BY class_name, subject_name
    """, (session["faculty"],)).fetchall()

    connection.close()

    return render_template(
        "subjects.html",
        subjects=subjects_list,
        school_classes=SCHOOL_CLASSES,
        school_subjects=SCHOOL_SUBJECTS
    )


# ==========================================
# ADD SUBJECT
# ==========================================

@app.route("/subjects/add", methods=["POST"])
def add_subject():

    if "faculty" not in session:
        return redirect(url_for("home"))

    subject_name = request.form.get(
        "subject_name", ""
    ).strip()

    class_name = request.form.get(
        "class_name", ""
    ).strip()

    if subject_name not in SCHOOL_SUBJECTS:
        flash("Please select a valid subject.", "error")
        return redirect(url_for("subjects"))

    if class_name not in SCHOOL_CLASSES:
        flash("Please select a valid school standard.", "error")
        return redirect(url_for("subjects"))

    connection = get_db_connection()

    try:

        connection.execute("""
            INSERT INTO subjects (
                subject_name,
                class_name,
                faculty_email
            )
            VALUES (?, ?, ?)
        """, (
            subject_name,
            class_name,
            session["faculty"]
        ))

        connection.commit()

        flash("Subject assigned successfully!", "success")

    except sqlite3.IntegrityError:

        flash("This subject is already assigned.", "error")

    finally:
        connection.close()

    return redirect(url_for("subjects"))


# ==========================================
# DELETE SUBJECT
# ==========================================

@app.route("/subjects/delete/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):

    if "faculty" not in session:
        return redirect(url_for("home"))

    connection = get_db_connection()

    connection.execute("""
        DELETE FROM subjects
        WHERE id = ? AND faculty_email = ?
    """, (subject_id, session["faculty"]))

    connection.commit()
    connection.close()

    flash("Subject assignment deleted.", "success")

    return redirect(url_for("subjects"))

# ==========================================
# TIMETABLE MANAGEMENT
# ==========================================

@app.route("/timetable")
def timetable():

    if "faculty" not in session:
        return redirect(url_for("home"))

    selected_class = request.args.get(
        "class_name", "all"
    ).strip()

    if selected_class != "all" and selected_class not in SCHOOL_CLASSES:
        selected_class = "all"

    connection = get_db_connection()

    if selected_class == "all":

        timetable_list = connection.execute("""
            SELECT *
            FROM timetable
            WHERE faculty_email = ?

            ORDER BY
                CASE day_of_week
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                END,
                period_number
        """, (session["faculty"],)).fetchall()

    else:

        timetable_list = connection.execute("""
            SELECT *
            FROM timetable
            WHERE faculty_email = ?
              AND class_name = ?

            ORDER BY
                CASE day_of_week
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                END,
                period_number
        """, (
            session["faculty"],
            selected_class
        )).fetchall()

    connection.close()

    return render_template(
        "timetable.html",
        timetable=timetable_list,
        school_classes=SCHOOL_CLASSES,
        school_subjects=SCHOOL_SUBJECTS,
        week_days=WEEK_DAYS,
        selected_class=selected_class
    )


# ==========================================
# ADD TIMETABLE ENTRY
# ==========================================

@app.route("/timetable/add", methods=["POST"])
def add_timetable():

    if "faculty" not in session:
        return redirect(url_for("home"))

    class_name = request.form.get(
        "class_name", ""
    ).strip()

    day_of_week = request.form.get(
        "day_of_week", ""
    ).strip()

    subject_name = request.form.get(
        "subject_name", ""
    ).strip()

    room = request.form.get(
        "room", ""
    ).strip()

    start_time = request.form.get(
        "start_time", ""
    ).strip()

    end_time = request.form.get(
        "end_time", ""
    ).strip()

    try:
        period_number = int(
            request.form.get("period_number", "")
        )
    except ValueError:
        flash("Please enter a valid period number.", "error")
        return redirect(url_for("timetable"))

    if class_name not in SCHOOL_CLASSES:
        flash("Please select a valid school standard.", "error")
        return redirect(url_for("timetable"))

    if day_of_week not in WEEK_DAYS:
        flash("Please select a valid weekday.", "error")
        return redirect(url_for("timetable"))

    if subject_name not in SCHOOL_SUBJECTS:
        flash("Please select a valid subject.", "error")
        return redirect(url_for("timetable"))

    if not 1 <= period_number <= 8:
        flash("Period number must be between 1 and 8.", "error")
        return redirect(url_for("timetable"))

    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")

        if start >= end:
            raise ValueError

    except ValueError:
        flash("Please enter valid class timings. End time must be after start time.", "error")
        return redirect(url_for("timetable"))

    connection = get_db_connection()

    try:

        connection.execute("""
            INSERT INTO timetable (
                class_name,
                day_of_week,
                period_number,
                start_time,
                end_time,
                subject_name,
                room,
                faculty_email
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            class_name,
            day_of_week,
            period_number,
            start_time,
            end_time,
            subject_name,
            room,
            session["faculty"]
        ))

        connection.commit()

        flash("Timetable entry added successfully!", "success")

    except sqlite3.IntegrityError:

        flash(
            "This faculty already has an entry for that class, day and period.",
            "error"
        )

    finally:
        connection.close()

    return redirect(url_for(
        "timetable",
        class_name=class_name
    ))


# ==========================================
# DELETE TIMETABLE ENTRY
# ==========================================

@app.route(
    "/timetable/delete/<int:entry_id>",
    methods=["POST"]
)
def delete_timetable(entry_id):

    if "faculty" not in session:
        return redirect(url_for("home"))

    connection = get_db_connection()

    connection.execute("""
        DELETE FROM timetable
        WHERE id = ?
          AND faculty_email = ?
    """, (
        entry_id,
        session["faculty"]
    ))

    connection.commit()
    connection.close()

    flash("Timetable entry deleted.", "success")

    return redirect(url_for("timetable"))

# ==========================================
# ANNOUNCEMENTS MANAGEMENT
# ==========================================

@app.route("/announcements")
def announcements():

    if "faculty" not in session:
        return redirect(url_for("home"))

    connection = get_db_connection()

    announcements_list = connection.execute("""
        SELECT *
        FROM announcements
        WHERE faculty_email = ?
        ORDER BY created_at DESC, id DESC
    """, (session["faculty"],)).fetchall()

    connection.close()

    return render_template(
        "announcements.html",
        announcements=announcements_list,
        school_classes=SCHOOL_CLASSES
    )


# ==========================================
# PUBLISH NEW ANNOUNCEMENT
# ==========================================

@app.route("/announcements/add", methods=["POST"])
def add_announcement():

    if "faculty" not in session:
        return redirect(url_for("home"))

    title = request.form.get("title", "").strip()

    message = request.form.get("message", "").strip()

    target_class = request.form.get(
        "target_class", "All School"
    ).strip()

    valid_targets = ["All School"] + SCHOOL_CLASSES

    if not title or not message:
        flash("Please enter both title and announcement details.", "error")
        return redirect(url_for("announcements"))

    if target_class not in valid_targets:
        flash("Please select a valid announcement audience.", "error")
        return redirect(url_for("announcements"))

    connection = get_db_connection()

    connection.execute("""
        INSERT INTO announcements (
            title,
            message,
            target_class,
            faculty_email
        )
        VALUES (?, ?, ?, ?)
    """, (
        title,
        message,
        target_class,
        session["faculty"]
    ))

    connection.commit()
    connection.close()

    flash("Announcement published successfully!", "success")

    return redirect(url_for("announcements"))


# ==========================================
# DELETE ANNOUNCEMENT
# ==========================================

@app.route(
    "/announcements/delete/<int:announcement_id>",
    methods=["POST"]
)
def delete_announcement(announcement_id):

    if "faculty" not in session:
        return redirect(url_for("home"))

    connection = get_db_connection()

    connection.execute("""
        DELETE FROM announcements
        WHERE id = ?
          AND faculty_email = ?
    """, (
        announcement_id,
        session["faculty"]
    ))

    connection.commit()
    connection.close()

    flash("Announcement deleted successfully.", "success")

    return redirect(url_for("announcements"))

# ==========================================
# FACULTY PROFILE MANAGEMENT
# ==========================================

@app.route("/profile", methods=["GET", "POST"])
def faculty_profile():

    if "faculty" not in session:
        return redirect(url_for("home"))

    faculty_email = session["faculty"]

    connection = get_db_connection()

    # Create a default profile for this faculty
    connection.execute("""
        INSERT OR IGNORE INTO faculty_profiles (
            faculty_email,
            faculty_name,
            faculty_id,
            department
        )
        VALUES (?, ?, ?, ?)
    """, (
        faculty_email,
        "Faculty Member",
        "FAC-001",
        "School Faculty"
    ))

    connection.commit()

    # Update faculty profile
    if request.method == "POST":

        faculty_name = request.form.get(
            "faculty_name", ""
        ).strip()

        faculty_id = request.form.get(
            "faculty_id", ""
        ).strip()

        department = request.form.get(
            "department", ""
        ).strip()

        qualification = request.form.get(
            "qualification", ""
        ).strip()

        phone = request.form.get(
            "phone", ""
        ).strip()

        address = request.form.get(
            "address", ""
        ).strip()

        if not faculty_name or not faculty_id or not department:

            flash(
                "Name, Faculty ID and Department are required.",
                "error"
            )

        else:

            connection.execute("""
                UPDATE faculty_profiles

                SET
                    faculty_name = ?,
                    faculty_id = ?,
                    department = ?,
                    qualification = ?,
                    phone = ?,
                    address = ?,
                    updated_at = CURRENT_TIMESTAMP

                WHERE faculty_email = ?

            """, (
                faculty_name,
                faculty_id,
                department,
                qualification,
                phone,
                address,
                faculty_email
            ))

            connection.commit()

            flash(
                "Faculty profile updated successfully!",
                "success"
            )

    # Retrieve saved profile
    profile = connection.execute("""
        SELECT *
        FROM faculty_profiles
        WHERE faculty_email = ?
    """, (faculty_email,)).fetchone()

    connection.close()

    return render_template(
        "profile.html",
        profile=profile
    )

# ==========================================
# FACULTY REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        faculty_name = request.form.get(
            "faculty_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not faculty_name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        connection = get_db_connection()

        try:

            cursor = connection.execute("""
                INSERT INTO faculty_accounts (
                    faculty_name,
                    faculty_email,
                    password_hash
                )
                VALUES (?, ?, ?)
            """, (
                faculty_name,
                email,
                generate_password_hash(password)
            ))

            account_id = cursor.lastrowid

            connection.execute("""
                INSERT INTO faculty_profiles (
                    faculty_email,
                    faculty_name,
                    faculty_id,
                    department
                )
                VALUES (?, ?, ?, ?)
            """, (
                email,
                faculty_name,
                f"FAC-{account_id:03d}",
                "School Faculty"
            ))

            connection.commit()

            flash(
                "Faculty account created successfully. Please log in.",
                "success"
            )

            return redirect(url_for("home"))

        except sqlite3.IntegrityError:

            flash(
                "This email address is already registered.",
                "error"
            )

        finally:
            connection.close()

    return render_template("register.html")

# =========================
# ASSIGNMENTS & HOMEWORK
# =========================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():
    if "faculty" not in session:
        return redirect(url_for("login"))

    faculty_email = session["faculty"]
    error = None
    # Ensure assignments table exists
    connection = sqlite3.connect("edumanage.db")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            work_type TEXT NOT NULL,
            description TEXT NOT NULL,
            class_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            due_date TEXT NOT NULL,
            max_marks REAL NOT NULL DEFAULT 0,
            faculty_email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        work_type = request.form.get("work_type", "").strip()
        description = request.form.get("description", "").strip()
        class_name = request.form.get("class_name", "").strip()
        subject = request.form.get("subject", "").strip()
        due_date = request.form.get("due_date", "").strip()

        try:
            max_marks = float(request.form.get("max_marks") or 0)
        except ValueError:
            max_marks = -1

        if not all([title, work_type, description, class_name,
                    subject, due_date]):
            error = "Please complete all required fields."
        elif work_type not in ["Assignment", "Homework"]:
            error = "Please select a valid work type."
        elif class_name not in SCHOOL_CLASSES:
            error = "Please select a valid class."
        elif subject not in SCHOOL_SUBJECTS:
            error = "Please select a valid subject."
        elif max_marks < 0:
            error = "Maximum marks cannot be negative."
        else:
            connection = sqlite3.connect("edumanage.db")
            connection.execute("""
                INSERT INTO assignments
                (title, work_type, description, class_name, subject,
                 due_date, max_marks, faculty_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, work_type, description, class_name, subject,
                due_date, max_marks, faculty_email
            ))
            connection.commit()
            connection.close()

            return redirect(url_for("assignments"))

    connection = sqlite3.connect("edumanage.db")
    connection.row_factory = sqlite3.Row

    assignment_list = connection.execute("""
        SELECT * FROM assignments
        WHERE faculty_email = ?
        ORDER BY due_date ASC, created_at DESC
    """, (faculty_email,)).fetchall()

    connection.close()

    return render_template(
        "assignments.html",
        assignments=assignment_list,
        school_classes=SCHOOL_CLASSES,
        school_subjects=SCHOOL_SUBJECTS,
        error=error
    )


@app.route("/assignments/delete/<int:assignment_id>", methods=["POST"])
def delete_assignment(assignment_id):
    if "faculty" not in session:
        return redirect(url_for("login"))

    connection = sqlite3.connect("edumanage.db")

    connection.execute("""
        DELETE FROM assignments
        WHERE id = ? AND faculty_email = ?
    """, (assignment_id, session["faculty"]))

    connection.commit()
    connection.close()

    return redirect(url_for("assignments"))


# ==========================================
# FACULTY LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ==========================================
# INITIALIZE DATABASE AND RUN APPLICATION
# ==========================================

init_db()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)