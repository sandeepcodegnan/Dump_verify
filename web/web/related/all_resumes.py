from flask import Flask, send_file, request,abort,jsonify
from flask_restful import Resource
from io import BytesIO
import zipfile
from web.db.db_utils import get_collection, get_gridfs

def get_student_collection():
    return get_collection('students')

class AllResumes(Resource):
    def __init__(self):
        super().__init__()
        self.student_collection = get_student_collection()
        self.fs = get_gridfs()

    def get(self):
        try:
            zip_data = BytesIO()
            
            with zipfile.ZipFile(zip_data, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file in self.fs.find():
                    file_data = file.read()
                    files = f"{file.filename}_{file._id}.pdf"
                    zip_file.writestr(files, file_data)

            zip_data.seek(0)

            return send_file(zip_data,
                            as_attachment=True,
                            download_name="all_resumes.zip",
                            mimetype="application/zip")

        except Exception as e:
            abort(500, description="Database query failed with GridFS files.")
        
        return jsonify({"error": "Unknown error occurred."}), 500