from flask import Flask, render_template, request, send_file, redirect, session
from PIL import Image
from PyPDF2 import PdfMerger
from io import BytesIO
import mysql.connector
import pandas as pd
import datetime
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- LOAD ENV VARIABLES ----------------

load_dotenv()

# ---------------- FLASK APP ----------------

app = Flask(__name__)

app.secret_key = "your_secret_key"

# ---------------- MYSQL DATABASE CONFIG ----------------

db_config = {

    "host": os.getenv("MYSQLHOST"),

    "user": os.getenv("MYSQLUSER"),

    "password": os.getenv("MYSQLPASSWORD"),

    "database": os.getenv("MYSQLDATABASE"),

    "port": int(os.getenv("MYSQLPORT"))

}

# ---------------- CREATE DATABASE TABLES ----------------

def init_db():

    db = mysql.connector.connect(**db_config)

    cursor = db.cursor()

    # ANALYTICS TABLE
    cursor.execute("""

    CREATE TABLE IF NOT EXISTS analytics (

        id INT AUTO_INCREMENT PRIMARY KEY,

        user_id INT,

        tool VARCHAR(255),

        time VARCHAR(255),

        file_count INT,

        size_kb INT

    )

""")

# USERS TABLE
    cursor.execute("""

        CREATE TABLE IF NOT EXISTS users (

            id INT AUTO_INCREMENT PRIMARY KEY,

            username VARCHAR(255),

            email VARCHAR(255),

            password VARCHAR(255)

        )

    """)

    db.commit()

    db.close()

    # ---------------- MASK EMAIL FUNCTION ----------------

def mask_email(email):

    parts = email.split("@")

    username = parts[0]

    domain = parts[1]

    if len(username) > 4:

        masked_username = username[:4] + "****"

    else:

        masked_username = username[0] + "***"

    return masked_username + "@" + domain

    

# RUN DATABASE SETUP
init_db()

# ---------------- HOME PAGE ----------------

@app.route('/')
def home():

    return render_template('home.html')

# ---------------- IMAGE TO PDF PAGE ----------------

@app.route('/image-to-pdf')
def image_to_pdf_page():

    if 'user_id' not in session:

        return redirect('/login')

    return render_template('image_to_pdf.html')

# ---------------- PDF MERGE PAGE ----------------

@app.route('/merge-pdf')
def merge_pdf_page():

    if 'user_id' not in session:

        return redirect('/login')

    return render_template('merge_pdf.html')

# ---------------- SIGNUP ----------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']

        email = request.form['email']

        password = generate_password_hash(request.form['password'])

        db = mysql.connector.connect(**db_config)

        cursor = db.cursor()

        cursor.execute("""

            INSERT INTO users

            (username, email, password)

            VALUES (%s, %s, %s)

        """, (

            username,

            email,

            password

        ))

        db.commit()

        db.close()

        return redirect('/login')

    return render_template('signup.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']

        password = request.form['password']

        db = mysql.connector.connect(**db_config)

        cursor = db.cursor(dictionary=True)

        cursor.execute("""

            SELECT * FROM users

            WHERE email=%s

        """, (email,))

        user = cursor.fetchone()

        db.close()

        print(user)

        print(password)

        if user:

            print(user['password'])

            print(check_password_hash(user['password'], password))

        if user and check_password_hash(user['password'], password):

            session['user_id'] = user['id']

            session['username'] = user['username']

            return redirect('/')

        else:

            return "Invalid credentials"

    return render_template('login.html')

# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# ---------------- IMAGE TO PDF CONVERTER ----------------

@app.route('/convert', methods=['POST'])
def convert():

    if 'user_id' not in session:

        return redirect('/login')

    files = request.files.getlist('images')

    image_list = []

    total_size = 0

    for file in files:

        if file:

            total_size += len(file.read())

            file.seek(0)

            img = Image.open(file).convert('RGB')

            image_list.append(img)

    if not image_list:

        return "No images uploaded"

    # CREATE PDF IN MEMORY
    pdf_bytes = BytesIO()

    image_list[0].save(

        pdf_bytes,

        format='PDF',

        save_all=True,

        append_images=image_list[1:]

    )

    pdf_bytes.seek(0)

    # SAVE ANALYTICS
    db = mysql.connector.connect(**db_config)

    cursor = db.cursor()

    cursor.execute("""

        INSERT INTO analytics

(user_id, tool, time, file_count, size_kb)

VALUES (%s, %s, %s, %s, %s)

    """, (

       
    session['user_id'],

    "image_to_pdf",

    str(datetime.datetime.now()),

    len(files),

    total_size // 1024


    ))

    db.commit()

    db.close()

    return send_file(

        pdf_bytes,

        as_attachment=True,

        download_name="converted.pdf"

    )

# ---------------- PDF MERGER ----------------

@app.route('/merge', methods=['POST'])
def merge():

    if 'user_id' not in session:

        return redirect('/login')

    files = request.files.getlist('pdfs')

    merger = PdfMerger()

    total_size = 0

    for file in files:

        if file:

            total_size += len(file.read())

            file.seek(0)

            merger.append(file)

    merged_pdf = BytesIO()

    merger.write(merged_pdf)

    merger.close()

    merged_pdf.seek(0)

    # SAVE ANALYTICS
    db = mysql.connector.connect(**db_config)

    cursor = db.cursor()

    cursor.execute("""

        INSERT INTO analytics

        (user_id, tool, time, file_count, size_kb)

        VALUES (%s, %s, %s, %s, %s)

    """, (

        session['user_id'],

        "pdf_merge",

        str(datetime.datetime.now()),

        len(files),

        total_size // 1024

    ))

    db.commit()

    db.close()

    return send_file(

        merged_pdf,

        as_attachment=True,

        download_name="merged.pdf"

    )


# ---------------- ANALYTICS ----------------

@app.route('/analytics')
def analytics():

    if 'user_id' not in session:

        return redirect('/login')

    db = mysql.connector.connect(**db_config)

    cursor = db.cursor(dictionary=True)

    cursor.execute("""

        SELECT

            analytics.id,

            users.email,

            analytics.tool,

            analytics.time,

            analytics.file_count,

            analytics.size_kb

        FROM analytics

        JOIN users

        ON analytics.user_id = users.id

        ORDER BY analytics.id ASC

    """)

    data = cursor.fetchall()

    db.close()

    # MASK EMAILS
    for row in data:

        row['email'] = mask_email(row['email'])

    return {

        "analytics": data

    }

# ---------------- EXPORT EXCEL ----------------

@app.route('/export-excel')
def export_excel():

    if 'user_id' not in session:

        return redirect('/login')

    db = mysql.connector.connect(**db_config)

    query = """

       SELECT

        analytics.id,

        users.email,

        analytics.tool,

        analytics.time,

        analytics.file_count,

        analytics.size_kb

    FROM analytics

    JOIN users

    ON analytics.user_id = users.id

    ORDER BY analytics.id ASC

    """

    df = pd.read_sql(query, db)
    
    if 'email' in df.columns:

        df['email'] = df['email'].apply(mask_email)

    db.close()

    excel_file = f"analytics_{int(datetime.datetime.now().timestamp())}.xlsx"

    df.to_excel(excel_file, index=False)

    return send_file(

        excel_file,

        as_attachment=True

    )

# ---------------- RUN APP ----------------

if __name__ == '__main__':

    port = int(os.environ.get("PORT", 5000))

    app.run(

        host='0.0.0.0',

        port=port,

        debug=True

    )
