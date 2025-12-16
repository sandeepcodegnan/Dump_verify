import json,os
import threading
import queue
import zipfile
from flask import Flask, Response, request, stream_with_context
from flask_restful import Resource, Api
from zipstream import ZipFile       
# pip install zipstream-new
from flask_restful import Resource
from web.jwt.auth_middleware import bde_required
from web.db.db_utils import get_collection, get_gridfs, get_s3_client, get_s3_bucket_name, get_from_s3
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
api = Api(app)

class DownloadResumes(Resource):
    def __init__(self):
        super().__init__()
        self.student_collection = get_collection('students')
        self.fs = get_gridfs()
        self.s3_client = get_s3_client()
        self.bucket_name = get_s3_bucket_name()

    @bde_required
    def post(self):
        student_ids = request.json.get("student_ids", [])
        if not student_ids:
            return {"error": "Missing required parameter: student_ids"}, 400

        # 1) Build the zipstream.ZipFile
        z = ZipFile(mode='w', compression=zipfile.ZIP_DEFLATED)
        for sid in student_ids:
            doc = self.student_collection.find_one({"id": sid})
            if not doc:
                continue

            filename = doc.get("name", sid) + ".pdf"
            
            # Try S3 first, fallback to GridFS
            s3_key = f"resumes/{sid}.pdf"
            s3_data = get_from_s3(s3_key)
            
            if s3_data:
                z.writestr(filename, s3_data)
            # else:
            #     # Fallback to GridFS
            #     file_doc = get_collection('fs_files').find_one({"filename": sid})
            #     if file_doc:
            #         grid_out = self.fs.get(file_doc["_id"])
            #         z.write_iter(filename, grid_out)

        # 2) Producer thread + bounded queue to keep data flowing
        q = queue.Queue(maxsize=10)
        def producer():
            for chunk in z:     # z yields bytes
                q.put(chunk)
            q.put(None)         # sentinel
        threading.Thread(target=producer, daemon=True).start()

        # 3) Generator that drains the queue
        def generate():
            while True:
                chunk = q.get()
                if chunk is None:
                    break
                yield chunk

        # 4) Stream to client with Nginx buffering disabled
        return Response(
            stream_with_context(generate()),
            mimetype="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="resumes.zip"',
                "X-Accel-Buffering": "no",
            }
        )

