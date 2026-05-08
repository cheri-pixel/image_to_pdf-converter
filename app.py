from flask import Flask, render_template, request, send_file
from PIL import Image
from PyPDF2 import PdfMerger
from io import BytesIO
import datetime
import sqlite3
import os
import pandas as pd

app = Flask(__name__)


# ---------------- DATABASE SETUP ----------------

def init_db():

    conn = sqlite3.connect('database.db')

    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            tool TEXT,

            time TEXT,

            file_count INTEGER,

            size_kb INTEGER

        )
    ''')

    conn.commit()

    conn.close()


# Run database setup
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

    # Get uploaded images
    files = request.files.getlist('images')

    image_list = []

    total_size = 0

    # Loop through uploaded images
    for file in files:

        if file:

            # Calculate file size
            total_size += len(file.read())

            # Reset file pointer
            file.seek(0)

            # Open image
            img = Image.open(file).convert('RGB')

            # Store image in list
            image_list.append(img)

    # Safety check
    if not image_list:

        return "No images uploaded"

    # Create memory PDF
    pdf_bytes = BytesIO()

    # Save images into PDF
    image_list[0].save(

        pdf_bytes,

        format='PDF',

        save_all=True,

        append_images=image_list[1:]

    )

    # Reset memory pointer
    pdf_bytes.seek(0)

    # ---------------- SAVE ANALYTICS ----------------

    conn = sqlite3.connect('database.db')

    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO analytics
        (tool, time, file_count, size_kb)

        VALUES (?, ?, ?, ?)
    ''', (

        "image_to_pdf",

        str(datetime.datetime.now()),

        len(files),

        total_size // 1024

    ))

    conn.commit()

    conn.close()

    # Send PDF to user
    return send_file(

        pdf_bytes,

        as_attachment=True,

        download_name="converted.pdf"

    )


# ---------------- PDF MERGER ----------------

@app.route('/merge', methods=['POST'])
def merge():

    # Get uploaded PDFs
    files = request.files.getlist('pdfs')

    merger = PdfMerger()

    total_size = 0

    # Loop through uploaded PDFs
    for file in files:

        if file:

            # Calculate file size
            total_size += len(file.read())

            # Reset pointer
            file.seek(0)

            # Add PDF
            merger.append(file)

    # Create memory PDF
    merged_pdf = BytesIO()

    # Write merged PDF
    merger.write(merged_pdf)

    merger.close()

    # Reset memory pointer
    merged_pdf.seek(0)

    # ---------------- SAVE ANALYTICS ----------------

    conn = sqlite3.connect('database.db')

    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO analytics
        (tool, time, file_count, size_kb)

        VALUES (?, ?, ?, ?)
    ''', (

        "pdf_merge",

        str(datetime.datetime.now()),

        len(files),

        total_size // 1024

    ))

    conn.commit()

    conn.close()

    # Send merged PDF
    return send_file(

        merged_pdf,

        as_attachment=True,

        download_name="merged.pdf"

    )


# ---------------- VIEW ANALYTICS ----------------

@app.route('/analytics')
def analytics():

    conn = sqlite3.connect('database.db')

    cursor = conn.cursor()

    cursor.execute('SELECT * FROM analytics')

    data = cursor.fetchall()

    conn.close()

    return {
        "analytics": data
    }

# ---------------- EXPORT TO EXCEL ----------------

@app.route('/export-excel')
def export_excel():

    # Connect database
    conn = sqlite3.connect('database.db')

    # Read analytics table
    query = "SELECT * FROM analytics"

    # Convert into dataframe
    df = pd.read_sql_query(query, conn)

    # Close database
    conn.close()

    # Create Excel file
    excel_file = "analytics.xlsx"

    # Save dataframe to Excel
    df.to_excel(excel_file, index=False)

    # Send Excel file to user
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
