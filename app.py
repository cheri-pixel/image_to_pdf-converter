from flask import Flask, render_template, request, send_file
from PIL import Image
from PyPDF2 import PdfMerger
from io import BytesIO
import mysql.connector
import pandas as pd
import datetime
import os

app = Flask(__name__)


# ---------------- MYSQL DATABASE CONNECTION ----------------

db_config = {

    "host": "mysql://root:lycEQVnNfyiCgtphSKRPFygeNAjOFIqs@turntable.proxy.rlwy.net:44147/railway",

    "user": "root",

    "password": "lycEQVnNfyiCgtphSKRPFygeNAjOFIqs",

    "database": "railway",

    "port": 3306

}


# ---------------- CREATE DATABASE TABLE ----------------

def init_db():

    db = mysql.connector.connect(**db_config)

    cursor = db.cursor()

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS analytics (

            id INT AUTO_INCREMENT PRIMARY KEY,

            tool VARCHAR(255),

            time VARCHAR(255),

            file_count INT,

            size_kb INT

        )

    """)

    db.commit()

    db.close()


# Initialize table
init_db()


# ---------------- HOME PAGE ----------------

@app.route('/')
def home():

    return render_template('home.html')


# ---------------- IMAGE TO PDF PAGE ----------------

@app.route('/image-to-pdf')
def image_to_pdf_page():

    return render_template('image_to_pdf.html')


# ---------------- PDF MERGE PAGE ----------------

@app.route('/merge-pdf')
def merge_pdf_page():

    return render_template('merge_pdf.html')


# ---------------- IMAGE TO PDF CONVERTER ----------------

@app.route('/convert', methods=['POST'])
def convert():

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

    # Create temporary PDF in memory
    pdf_bytes = BytesIO()

    image_list[0].save(

        pdf_bytes,

        format='PDF',

        save_all=True,

        append_images=image_list[1:]

    )

    pdf_bytes.seek(0)

    # ---------------- SAVE ANALYTICS ----------------

    db = mysql.connector.connect(**db_config)

    cursor = db.cursor()

    cursor.execute("""

        INSERT INTO analytics

        (tool, time, file_count, size_kb)

        VALUES (%s, %s, %s, %s)

    """, (

        "image_to_pdf",

        str(datetime.datetime.now()),

        len(files),

        total_size // 1024

    ))

    db.commit()

    db.close()

    # Send PDF
    return send_file(

        pdf_bytes,

        as_attachment=True,

        download_name="converted.pdf"

    )


# ---------------- PDF MERGER ----------------

@app.route('/merge', methods=['POST'])
def merge():

    files = request.files.getlist('pdfs')

    merger = PdfMerger()

    total_size = 0

    for file in files:

        if file:

            total_size += len(file.read())

            file.seek(0)

            merger.append(file)

    # Create merged PDF in memory
    merged_pdf = BytesIO()

    merger.write(merged_pdf)

    merger.close()

    merged_pdf.seek(0)

    # ---------------- SAVE ANALYTICS ----------------

    db = mysql.connector.connect(**db_config)

    cursor = db.cursor()

    cursor.execute("""

        INSERT INTO analytics

        (tool, time, file_count, size_kb)

        VALUES (%s, %s, %s, %s)

    """, (

        "pdf_merge",

        str(datetime.datetime.now()),

        len(files),

        total_size // 1024

    ))

    db.commit()

    db.close()

    # Send merged PDF
    return send_file(

        merged_pdf,

        as_attachment=True,

        download_name="merged.pdf"

    )


# ---------------- ANALYTICS ROUTE ----------------

@app.route('/analytics')
def analytics():

    db = mysql.connector.connect(**db_config)

    cursor = db.cursor()

    cursor.execute("""

        SELECT * FROM analytics
        ORDER BY id ASC

    """)

    data = cursor.fetchall()

    db.close()

    return {

        "analytics": data

    }


# ---------------- EXPORT EXCEL ----------------

@app.route('/export-excel')
def export_excel():

    db = mysql.connector.connect(**db_config)

    query = """

        SELECT * FROM analytics
        ORDER BY id ASC

    """

    df = pd.read_sql(query, db)

    db.close()

    # Create unique filename
    excel_file = f"analytics_{int(datetime.datetime.now().timestamp())}.xlsx"

    # Save Excel
    df.to_excel(excel_file, index=False)

    # Download Excel
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
