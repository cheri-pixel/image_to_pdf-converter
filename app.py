from flask import Flask, render_template, request, send_file
from PIL import Image
from PyPDF2 import PdfMerger
from io import BytesIO
import datetime
import os

app = Flask(__name__)

# Analytics storage
analytics = []


# ---------------- HOME PAGE ----------------
@app.route('/')
def index():
    return render_template('index.html')


# ---------------- IMAGE TO PDF ----------------
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

            # Open image and convert to RGB
            img = Image.open(file).convert('RGB')

            # Store image in list
            image_list.append(img)

    # Safety check
    if not image_list:
        return "No images uploaded"

    # Create temporary memory PDF
    pdf_bytes = BytesIO()

    # Save images into one PDF
    image_list[0].save(
        pdf_bytes,
        format='PDF',
        save_all=True,
        append_images=image_list[1:]
    )

    # Reset memory pointer
    pdf_bytes.seek(0)

    # Store analytics only
    analytics.append({
        "tool": "image_to_pdf",
        "time": str(datetime.datetime.now()),
        "file_count": len(files),
        "size_kb": total_size // 1024
    })

    # Send PDF to user
    return send_file(
        pdf_bytes,
        as_attachment=True,
        download_name="converted.pdf"
    )


# ---------------- PDF MERGE ----------------
@app.route('/merge', methods=['POST'])
def merge():

    # Get uploaded PDFs
    files = request.files.getlist('pdfs')

    merger = PdfMerger()

    total_size = 0

    # Loop through PDFs
    for file in files:

        if file:

            # Calculate size
            total_size += len(file.read())

            # Reset pointer
            file.seek(0)

            # Add PDF to merger
            merger.append(file)

    # Create memory file
    merged_pdf = BytesIO()

    # Write merged PDF
    merger.write(merged_pdf)

    # Close merger
    merger.close()

    # Reset pointer
    merged_pdf.seek(0)

    # Store analytics
    analytics.append({
        "tool": "pdf_merge",
        "time": str(datetime.datetime.now()),
        "file_count": len(files),
        "size_kb": total_size // 1024
    })

    # Send merged PDF
    return send_file(
        merged_pdf,
        as_attachment=True,
        download_name="merged.pdf"
    )


# ---------------- ANALYTICS ----------------
@app.route('/analytics')
def view_analytics():
    return {"data": analytics}


# ---------------- RUN APP ----------------
if __name__ == '__main__':

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )