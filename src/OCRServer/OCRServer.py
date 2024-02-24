from flask import Flask, request, render_template,jsonify
from datetime import datetime
import time
import os
import hashlib
from src.ImageProcessor.ImageProcessor import ImageProcessor
from src.OCRUtility.OCRUtility import OCRUtility


class OCRServer:
    """
    OCRServer: Flask web server for Optical Character Recognition (OCR).

    Attributes:
        - image_processor (ImageProcessor): Instance of the ImageProcessor class for image processing.
        - ocr_utility (OCRUtility): Instance of the OCRUtility class for OCR-related utility functions.

    Methods:
        - __init__(self, debug=False, host='0.0.0.0', ssl_context=None): Constructor method to initialize the OCRServer.
        - run(self): Run the Flask web server.
        - index(self): Route handler for the index page displaying server information.
        - process_image(self): Route handler for processing uploaded images and extracting text using OCR.
        - update_status(self, new_status): Update the server status.
        - write_log(self, message): Write a log message to the requests log.
    """

    image_processor = ImageProcessor()
    ocr_utility = OCRUtility()

    def __init__(self, debug=False, host='0.0.0.0', ssl_context=None):
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.status = "idle"
        self.uptime_start_time = time.time()
        self.processed_requests = 0
        self.requests_log = []

        # Define routes
        self.app.route('/')(self.index)
        self.app.route('/process_image', methods=['POST'])(self.process_image)

        self.debug = debug
        self.host = host
        self.ssl_context = ssl_context


        # Create a temporary folder for uploaded photos
        self.tmp_folder = 'tmp_post'
        if not os.path.exists(self.tmp_folder):
            os.makedirs(self.tmp_folder)

    def run(self):
        """Run the Flask web server."""
        self.update_status("active")
        self.app.run(debug=self.debug, host=self.host, ssl_context=self.ssl_context)

    def index(self):

        """Route handler for the index page displaying server information."""

        today=self.get_current_datestamp()
        print(today)

        uptime = round(time.time() - self.uptime_start_time, 2)
        ip_address = request.remote_addr
        server_info = f"{self.tmp_folder}"
        log_entries = []

        for i, log_entry in enumerate(reversed(self.requests_log), start=1):
            log_array = log_entry.split('\n')
            for each in log_array:
                log_entries.append(f"{each}\n")

        return render_template('index.html', status=self.status, indicator=self.status.lower(), uptime=uptime, processed_requests=self.processed_requests,
                               current_date=today[0], server_info=server_info, log_entries=log_entries)
    def process_image(self):
        """Route handler for processing uploaded images and extracting text using OCR."""
        try:
            log_entry = []

            # Log request headers
            request_source_address= request.remote_addr
            log_entry.append(f"SRC: {request_source_address}")
            self.write_log(log_entry)

            # Create a temporary path for the uploaded file
            tmp_file_path = os.path.join(self.tmp_folder, 'uploaded_photo.jpg')

            # Save the uploaded file to the temporary folder
            uploaded_file = request.files['image']
            uploaded_file.save(tmp_file_path)

            # Use OCRUtility to generate a unique filename and save the file
            sanitized_name = self.ocr_utility.sanitize_name(uploaded_file.filename)
            saved_path = self.ocr_utility.save_uploaded_file(uploaded_file, self.tmp_folder, sanitized_name)

            # Use ImageProcessor to process and extract text
            extracted_text = self.image_processor.process_and_extract_text(tmp_file_path)

            # Update status and log
            self.update_status("Processing")
            self.processed_requests += 1
            # self.requests_log.append(f"Processed request #{self.processed_requests}: {extracted_text}")
            response_data = {
                "status": "success",
                "message": "Image processed successfully!",
                "extracted_text": extracted_text
            }
            self.update_status("ready")


            return jsonify(response_data)


        except Exception as e:
            # Handle exceptions and return an error response
            self.update_status='error'
            error_message = f"Error processing image: {e}"
            response_data = {
                "status": "error",
                "message": error_message
            }
            return jsonify(response_data), 500

    @staticmethod
    def get_request_ip():
        ip_address=request.remote_addr
        return f"Server IP Address: {ip_address}"

    @staticmethod
    def get_current_datestamp():
        """
        Returns an array with the current date and time.

        Returns:
        - list: Array containing [YYYY-MM-DD, HH:mm:ss]
        """
        current_datetime = datetime.now()
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_time = current_datetime.strftime("%H:%M:%S")

        return [current_date,current_time]


    def update_status(self, new_status):
        self.status = new_status

    def write_log(self, message):
        """Write a log message to the requests log."""
        current_datetime = self.get_current_datestamp()
        request_headers = dict(request.headers)
        unique_id = self.generate_unique_id()



        log_entry = f"\n[{current_datetime[0]}:{current_datetime[1]}] Unique ID: {unique_id}\n"
        for key, value in request_headers.items():
            log_entry += f"{key}: {value}\n"

        log_entry += f"{message}\n"

        self.requests_log.append(log_entry)

    def generate_unique_id(self):
        """Generate a unique identifier based on timestamp with milliseconds."""
        timestamp_ms = int(time.time() * 1000)  # Convert current time to milliseconds
        hash_object = hashlib.md5(str(timestamp_ms).encode())
        return hash_object.hexdigest()

    def update_status(self, new_status):
        self.status = new_status


