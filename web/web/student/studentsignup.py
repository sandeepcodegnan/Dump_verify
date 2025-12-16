from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import StudentResource,student_required
from web.db.db_utils import get_collection, get_client, get_db

def get_student_collection():
    return get_collection('students')
from datetime import datetime
from gridfs import GridFS
from PIL import Image
import os ,io
import  bcrypt
from PIL import Image
import os, io
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables 
load_dotenv()

def compress_image(image_bytes, target_size_kb=10):
    """
    Compress the input image bytes so that its size is approximately at most target_size_kb (in KB).
    The function uses Pillow to open, convert, and (if needed) resize the image.
    Returns the compressed image bytes.
    """
    # Open the image from bytes
    image_io = io.BytesIO(image_bytes)
    try:
        image = Image.open(image_io)
    except Exception as e:
        raise ValueError("Invalid image file provided.")
   
    # Convert to RGB if necessary (JPEG requires RGB)
    if image.mode != "RGB":
        image = image.convert("RGB")
   
    quality = 85  # Starting quality setting
    compressed_io = io.BytesIO()
    image.save(compressed_io, format="JPEG", quality=quality)
    size_kb = len(compressed_io.getvalue()) / 1024

    # First, reduce quality until the size is under target_size_kb or quality reaches a threshold.
    while size_kb > target_size_kb and quality > 10:
        quality -= 5
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024

    # If quality reduction alone is insufficient, resize the image.
    if size_kb > target_size_kb:
        width, height = image.size
        # Calculate a scaling factor based on current size versus target size.
        factor = (target_size_kb / size_kb) ** 0.5 
        new_width = max(1, int(width * factor))
        new_height = max(1, int(height * factor))
        image = image.resize((new_width, new_height), Image.LANCZOS) 
        quality = 85  # Reset quality after resizing
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024
       
        # Further reduce quality if needed.
        while size_kb > target_size_kb and quality > 10:
            quality -= 5
            compressed_io = io.BytesIO()
            image.save(compressed_io, format="JPEG", quality=quality)
            size_kb = len(compressed_io.getvalue()) / 1024

    compressed_io.seek(0)
    return compressed_io.getvalue()


class StudentSignup(Resource):
    def __init__(self):
        super().__init__()
        self.client = get_client()
        self.db = get_db()
        self.collection = get_student_collection()
        
        # Initialize S3 client using environment variables
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            # Use S3_BUCKET_NAME from environment variables
            self.bucket_name = os.getenv('S3_BUCKET_Students_Files')
            if not self.bucket_name:
                print("WARNING: S3 bucket name not configured in environment variables")
                # Set a default bucket name
                self.bucket_name = "codegnan-students-files"  # Default bucket name
        except Exception as e:
            print(f"Warning: Could not initialize S3 client: {e}")
            self.s3_client = None
            self.bucket_name = None
            
        # Create uploads directory for local storage fallback
        # uploads_dir = os.path.join(os.getcwd(), 'uploads')
        # if not os.path.exists(uploads_dir):
        #     try:
        #         os.makedirs(uploads_dir)
        #     except Exception as e:
        #         print(f"Warning: Could not create uploads directory: {e}")
        
    def upload_file_to_s3(self, file_data, key, content_type):
        """Helper method to upload a file to S3
        Args:
            file_data: The binary data of the file to upload
            key: The S3 object key (path/filename)
            content_type: The MIME type of the file
        Returns:
            dict: Dictionary containing success status and file URL or error message
        """
        if not self.bucket_name:
            print("Error: S3 bucket name is not configured")
            return {
                "success": False,
                "error": "S3 bucket name is not configured"
            }
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type
            )
            return {
                "success": True,
                "url": f"https://{self.bucket_name}.s3.amazonaws.com/{key}",
                "key": key
            }
        except ClientError as e:
            error_message = str(e)
            print(f"Error uploading file to S3: {error_message}")
                        
            
    def check_and_delete_s3_file(self, key):
        """Check if a file exists in S3 and delete it if it does
        Args:
            key: The S3 object key to check and delete
        Returns:
            bool: True if file was deleted or didn't exist, False if deletion failed
        """
        if not self.bucket_name:
            print("Error: S3 bucket name is not configured")
            return False
            
        try:
            # Try to delete the object directly without checking if it exists first
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            except ClientError as delete_error:
                print(f"Warning: Could not delete S3 object: {delete_error}")
                
            # Also try to delete local file if it exists
            local_path = os.path.join(os.getcwd(), 'uploads', key)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    print(f"Deleted local file: {local_path}")
                except Exception as local_error:
                    print(f"Error deleting local file: {local_error}")
            
            return True
        except Exception as e:
            print(f"Error in check_and_delete_s3_file: {e}")
            return False
            
    def ensure_bucket_exists(self):
        """Assume the bucket exists and return True"""
        # Skip bucket existence check due to permission issues
        # Just assume the bucket exists and let the upload operation determine if it's accessible
        return True
            
    def generate_presigned_url(self, key, expiration=3600):
        """Generate a presigned URL for accessing an S3 object
        Args:
            key: The S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
        Returns:
            str or None: Presigned URL if successful, None if failed
        """
        if not self.bucket_name:
            print("Error: S3 bucket name is not configured")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
                        
            return None

    @student_required
    def post(self):
        # Extract data from the request
        data = request.form
        timestamp = datetime.now().isoformat()
        if data.get("qualification") in ['Class X', 'Intermediate','Diploma','ITI']:
            age = int(data.get('age'))
            arrears=data.get("arrears")
            arr_cnt = data.get("arrearsCount")
            city = data.get("cityName")
            collegeName = data.get("collegeName")
            collegeUSNNumber = data.get("collegeUSNNumber")
            department = data.get("department")
            Dob = data.get('dob')
            email = data.get('email')
            gender = data.get('gender')
            githubLink=data.get("githubLink")
            highestGraduationpercentage = float(data.get("highestGraduationPercentage"))
            name = data.get('name')
            status = data.get('profileStatus')
            qualification = data.get("qualification")
            state = data.get('state')
            studentSkills = data.getlist("studentSkills[]")
            tenthyear = data.get('tenthPassoutYear')
            tenthStandard = float(data.get("tenthStandard"))
            twelfthStandard = float(data.get("twelfthStandard"))
            twelfthyear = data.get('twelfthPassoutYear')        
            yearOfPassing = data.get("yearOfPassing")
            bloodgroup = data.get("bloodGroup")
            
            std_data = {
                "timestamp": timestamp,
                "name": name,
                "DOB":Dob,
                "age": age,
                "gender":gender,
                "state": state,
                "qualification": qualification,
                "yearOfPassing": yearOfPassing,
                "city": city,
                "department": department,
                "collegeName": collegeName,
                "highestGraduationpercentage": highestGraduationpercentage,
                "studentSkills": studentSkills,
                "tenthStandard": tenthStandard,
                "twelfthStandard":twelfthStandard,
                "collegeUSNNumber":collegeUSNNumber,
                "githubLink":githubLink,
                "TenthPassoutYear":tenthyear,
                "TwelfthPassoutYear":twelfthyear,
                "arrears":arrears,
                "ArrearsCount":arr_cnt,
                "ProfileStatus":status,
                "bloodGroup":bloodgroup
            }
            result = self.collection.find_one({"email":email})

            self.collection.update_many({"email":email}, {"$set": std_data})
            return {"message": "Student signup successful", "student": std_data }, 201
        else:
            email = data.get('email')
            name = data.get('name')
            Dob = data.get('dob')
            age = int(data.get('age'))
            gender = data.get('gender')
            password = data.get('password')
            h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            state = data.get('state')
            qualification = data.get("qualification")
            city = data.get("cityName")
            department = data.get("department")
            yearOfPassing = data.get("yearOfPassing")
            collegeName = data.get("collegeName")
            highestGraduationpercentage = float(data.get("highestGraduationPercentage"))
            studentSkills = data.getlist("studentSkills[]")
            tenthStandard = float(data.get("tenthStandard"))
            twelfthStandard = float(data.get("twelfthStandard"))
            resume = request.files.get('resume')
            resume_file = resume.read()
            profile = request.files.get('profilePic')
            profile_bytes = profile.read()
            try:
                pro_file = compress_image(profile_bytes, target_size_kb=10)
            except Exception as e:
                return {"error": "Failed to compress profile image: " + str(e)}, 400
            collegeUSNNumber = data.get("collegeUSNNumber")
            githubLink=data.get("githubLink")
            arrears=data.get("arrears")
            arr_cnt = data.get("arrearsCount")
            tenthyear = data.get('tenthPassoutYear')
            twelfthyear = data.get('twelfthPassoutYear')
            status = data.get('profileStatus')
            bloodgroup = data.get("bloodGroup")

            if not [highestGraduationpercentage,pro_file,resume_file,studentSkills,yearOfPassing]:
                return {"error": "Missing required fields"}, 400
            # Database already initialized via db_utils
        
            # Insert student signup data into MongoDB
            student_data = {
                "timestamp": timestamp,
                "name": name,
                "DOB":Dob,
                "password": h_pwd,
                "age": age,
                "gender":gender,
                "state": state,
                "qualification": qualification,
                "yearOfPassing": yearOfPassing,
                "city": city,
                "department": department,
                "collegeName": collegeName,
                "highestGraduationpercentage": highestGraduationpercentage,
                "studentSkills": studentSkills,
                "tenthStandard": tenthStandard,
                "twelfthStandard":twelfthStandard,
                "collegeUSNNumber":collegeUSNNumber,
                "githubLink":githubLink,
                "TenthPassoutYear":tenthyear,
                "TwelfthPassoutYear":twelfthyear,
                "arrears":arrears,
                "ArrearsCount":arr_cnt,
                "ProfileStatus":status,
                "bloodGroup":bloodgroup
            }
            result = self.collection.find_one({"email":email})
            ids = result["id"]
            std_id = result['studentId']
            self.collection.update_many({"email":email}, {"$set": student_data})
            #student_data['_id'] = str(result.inserted_id)
                
            # Save the resume file to S3 with student ID as filename
            resume_key = f"resumes/{ids}.pdf"  # Assuming PDF format, adjust if needed
            resume_result = self.upload_file_to_s3(
                file_data=resume_file,
                key=resume_key,
                content_type='application/pdf'  # Adjust content type if needed
            )
            
            if not resume_result["success"]:
                error_msg = resume_result.get("error", "Unknown error")
                return {"error": f"Failed to upload resume: {error_msg}"}, 500
                
            # Store only the resume URL in MongoDB
            student_data['resume_url'] = resume_result["url"]
                
            # Save the profile picture to S3 with student ID as filename
            profile_key = f"profile_pics/{std_id}.jpg"  # Using jpg format for compressed images
            profile_result = self.upload_file_to_s3(
                file_data=pro_file,
                key=profile_key,
                content_type='image/jpeg'
            )
            
            if not profile_result["success"]:
                error_msg = profile_result.get("error", "Unknown error")
                return {"error": f"Failed to upload profile picture: {error_msg}"}, 500
                
            # Store only the profile URL in MongoDB
            student_data['profile_url'] = profile_result["url"]
                
            # Update MongoDB with the complete student data including file URLs
            self.collection.update_many({"email":email}, {"$set": student_data})
            
            #self.send_email(name, email)
            return {"message": "Student signup successful", "student": student_data }, 201
        
    @student_required 
    def put(self):
        data = request.form
        timestamp = datetime.now().isoformat()

        age = int(data.get('age'))
        arrears=data.get("arrears")
        arr_cnt = data.get("arrearsCount")
        city = data.get("cityName")
        collegeName = data.get("collegeName")
        collegeUSNNumber = data.get("collegeUSNNumber")
        department = data.get("department")
        Dob = data.get('dob')
        email = data.get('email')
        gender = data.get('gender')
        githubLink=data.get("githubLink")
        highestGraduationpercentage = float(data.get("highestGraduationPercentage"))
        name = data.get('name')
        status = data.get('profileStatus')
        qualification = data.get("qualification")
        state = data.get('state')
        studentSkills = data.getlist("studentSkills[]")
        tenthyear = data.get('tenthPassoutYear')
        tenthStandard = float(data.get("tenthStandard"))
        twelfthStandard = float(data.get("twelfthStandard"))
        twelfthyear = data.get('twelfthPassoutYear')        
        yearOfPassing = data.get("yearOfPassing")
        bloodgroup = data.get("bloodGroup")
        
        std_data = {
            "timestamp": timestamp,
            "name": name,
            "DOB":Dob,
            "age": age,
            "gender":gender,
            "state": state,
            "qualification": qualification,
            "yearOfPassing": yearOfPassing,
            "city": city,
            "department": department,
            "collegeName": collegeName,
            "highestGraduationpercentage": highestGraduationpercentage,
            "studentSkills": studentSkills,
            "tenthStandard": tenthStandard,
            "twelfthStandard":twelfthStandard,
            "collegeUSNNumber":collegeUSNNumber,
            "githubLink":githubLink,
            "TenthPassoutYear":tenthyear,
            "TwelfthPassoutYear":twelfthyear,
            "arrears":arrears,
            "ArrearsCount":arr_cnt,
            "ProfileStatus":status,
            "bloodGroup":bloodgroup
        }
        result = self.collection.find_one({"email":email})

        self.collection.update_many({"email":email}, {"$set": std_data})
        return {"message": "Student  successful", "student": std_data }, 200