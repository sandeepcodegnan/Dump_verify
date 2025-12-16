from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_restful import Resource
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
os.chdir(os.path.abspath(os.curdir))
from flask_restful import Api
import json
import urllib.parse
from pymongo import MongoClient 
from web.related.refreshboard import GoogleSheetReader
from web.related.codegnan import CodeGnan

#admins
from web.admins.bdesignup import BdeSignup
from web.admins.manager import ManagerLogin
from web.admins.Admin import SuperAdmin
from web.admins.mentor import Mentors
from web.admins.adms_count import AllAdminsCount
from web.admins.curriculam import CurriCulum
from web.admins.practice_mentor import PracticeMentors
from web.admins.sales import Sales

#managers
from web.managers.add_student import Add_Student
from web.managers.batch_creat import CreateBatch
from web.managers.leave_manager import ManagerLeaveupdated
from web.managers.schedules import ScheduleBatches
from web.managers.get_schedule_data import GetScheduledData 

#mentors
from web.mentors.mentor_curriculum import Mentor_CurriCulum
from web.mentors.mentors_stds import ListofStudentsForMentor

#attendance system
from web.attend.attends_1 import Attendace
from web.attend.attends_data import AttendData
from web.attend.attends_check import AttendCheck
from web.attend.attends_get import GetAttendance
from web.attend.batch_attends import GetBatchwiseAttendance
from web.attend.miss_attends import GetMissingAttendance
from web.attend.download_missing_attends import DownloadAttendance

#BDES
from web.bdes.get_job_details import GetJobDetails
from web.bdes.resumedownload import DownloadResumes
from web.bdes.jobsapplied import GetAppliedJobsList
from web.bdes.applyforjobs import JobApplication
from web.bdes.list_openings import ListOpenings
from web.bdes.jobpostings import JobPosting  
from web.bdes.edit_job import EditJob
from web.bdes.download_applied_students import DownloadAppliedStudentList

#jobs Interviews
from web.jobs.select_all import UpdateJobApplicants
from web.jobs.selected_students_list import Selected_Stutents_list
from web.jobs.interview_rounds import InterviewRounds
from web.jobs.student_rounds import Student_Rounds

#certificates
from web.certificates.cretify import Certificates
from web.certificates.download_files import Dowload_certificates
from web.jwt.refresh_token import RefreshToken

#for all common apis
from web.related.student_OTP import StudentVerification
from web.related.validateOTP import ValidateOTP
from web.related.all_resumes import AllResumes
from web.related.forgotpwd import ForgotPwd
from web.related.updatepwd import Updatepassword
from web.related.all_login import Logins
from web.related.logout import Logout
from web.related.Edu_branches import EducationalBranches
from web.related.skills import Skills
from web.related.course import Subjects
from web.related.all_locations import Locations
from web.related.techstacks import TechStack
from web.related.designation import Designation
from web.related.download_excel import DownloadAllStudents

#Students Module
from web.student.update_resume import UpdateResume
from web.student.get_student_details import GetStudentDetails
from web.student.students_location import StudentsByLocation
from web.student.studentsapplied import GetAppliedStudentList
from web.student.search_student.search_student import Search_Students
from web.student.studentsignup import StudentSignup
from web.student.all_student import GetAllStudents
from web.student.ats import ATSCheck
from web.student.std_curiculum import StudentsCurriculum
from web.student.std_leave import StudentLeaveRequest
from web.student.pro import Profile_pic
from web.student.students_eligible import StudentEligibleJobs
from web.student.zoho_add import Add_zoho_Student
from web.student.zoho_invoice import zoho_Invoice

#sandeep
from web.related.active_batches import ActiveBatches

# Direct Daily_Exam API imports - Clean Architecture
from web.Exam.Daily_Exam.api.examiner_api import (
    CheckExamStatus, GetExamData, GenerateExamPaper, ExaminerExamDayList, ExaminerBatchReports
)
from web.Exam.Daily_Exam.api.student_api import (
    GetAvailableExams, StartExam, CodeExecution, SubmitExam, ExamQuestionReview, StudentExamSummary, StudentExamDetail, ExamBatchLeaderboard, GetConductedExamDates
)
from web.Exam.Daily_Exam.api.mentor_api import MentorExamDayList

# Interview API
from web.Exam.Interview.api.interview_api import GetInterviewData

# Window Configuration APIs (without toggle)
from web.Exam.Daily_Exam.api.admin_window_api import WindowConfigResource, WindowConfigDetailResource

# Exam Toggle APIs
from web.Exam.Daily_Exam.api.admin_exam_toggle_api import ExamToggleResource, ExamToggleDetailResource

from web.Exam.exam_statistics.examreport import ExamReport
from web.Exam.exam_statistics.batch_report import BatchReport

# Testing Module - Direct API Imports
from web.Exam.Testing.api.upload_api import UploadAPI
from web.Exam.Testing.api.question_api import QuestionAPI
from web.Exam.Testing.api.curriculum_api import CurriculumAPI
from web.Exam.Testing.api.subjects_api import SubjectsAPI
from web.Exam.Testing.api.verification_api import VerificationAPI
from web.Exam.Testing.api.submission_api import SubmissionAPI
from web.Exam.Testing.api.progress_api import TesterOverallAPI, TesterByIdAPI, TesterSubjectDetailsAPI
from web.Exam.Testing.api.dump_api import DumpAPI
from web.Exam.Testing.api.execution_api import ExecutionAPI
from web.Exam.Testing.api.tester_api import TesterAPI

from web.Exam.Parent_Reports.Parent_Whatsapp_report.report_processor_api import ReportProcessorAPI
from web.Exam.Parent_Reports.Parent_Whatsapp_report.whatsapp.whatsapp_api import WhatsAppAPI
from web.Exam.Parent_Reports.Parent_Whatsapp_report.task_status_api import TaskStatusAPI
from web.Exam.Parent_Reports.Parent_Whatsapp_report.period_api import PeriodAPI

from web.Exam.central_whatsapp_notifications.wa_status_apis import WaParentStatusDelivery,WaDailyExamDelivery

# Code playground
from web.Exam.codeplayground.question_execution import QuestionExecution
from web.Exam.codeplayground.cpsubmission import CpSubmissions
from web.Exam.codeplayground.cpprogress import CpProgress
from web.Exam.codeplayground.cpcurriculum import cpcurriculum
from web.Exam.codeplayground.leaderboard import Leaderboard
from web.Exam.codeplayground.questions_with_progress import QuestionsWithProgress
from web.Exam.Flags.feature_middleware import create_feature_aware_resource
from web.Exam.Flags.feature_check_api import CodePlaygroundFeatureCheck

#flag code playground - middleware and admin APIs
from web.Exam.Flags.flag_api import FeatureToggle, LocationFeatureToggle, BatchFeatureToggle, HierarchicalFeatureView

# Course Subjects API
from web.Exam.codeplayground.subjects import GetFirstSubject

# MySQL Template Management
from web.Exam.mysql_templates.template_manager import TemplateUpload, TemplateList, TemplateTableNames, TemplateTableData

with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

config_data["MONGO_CONFIG"]["url"]     = os.getenv("DB_URL",config_data["MONGO_CONFIG"]["url"])
config_data["MONGO_CONFIG"]["db_name"] = os.getenv("DB_NAME",config_data["MONGO_CONFIG"]["db_name"])

MONGO_CONFIG = config_data['MONGO_CONFIG']
MONGO_CONFIG12 = config_data['MONGO_CONFIG']['url']

class HealthCheck(Resource):
    def get(self):
        return {"message": "Welcome to Codegnan...!, This is production environment server...! start using apis"}, 200

class MyFlask(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uri = MONGO_CONFIG['url']
        parsed_uri = urllib.parse.urlparse(uri)

        # Escape credentials only if they exist
        if parsed_uri.username and parsed_uri.password:
            escaped_username = urllib.parse.quote_plus(parsed_uri.username)
            escaped_password = urllib.parse.quote_plus(parsed_uri.password)

            # Reconstruct URI with escaped username and password
            # Example: mongodb://user:pass@host/db -> mongodb://escaped_user:escaped_pass@host/db
            escaped_netloc = f"{escaped_username}:{escaped_password}@{parsed_uri.hostname}"
            if parsed_uri.port:
                escaped_netloc += f":{parsed_uri.port}"

            escaped_uri = urllib.parse.urlunparse((
                parsed_uri.scheme,
                escaped_netloc,
                parsed_uri.path,
                parsed_uri.params,
                parsed_uri.query,
                parsed_uri.fragment
            ))
        else:
            # No credentials present, use URI as-is
            escaped_uri = uri
        self.client = MongoClient(
            escaped_uri,
            serverSelectionTimeoutMS=30000,  # 30 seconds
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            maxPoolSize=50,
            retryWrites=True)
        self.db = self.client[MONGO_CONFIG['db_name']]
        self.collection = self.db[MONGO_CONFIG['collection_name']]

        self.bde_login_collection = MONGO_CONFIG["BDE_LOGIN"]["collection_name"]
        self.student_collection = MONGO_CONFIG["STUDENT_LOGIN"]["collection_name"]
        self.job_details_collection = MONGO_CONFIG["JOBS"]["collection_name"]
        self.company_login_collection = MONGO_CONFIG["COMPANY"]["collection_name"]
        self.otp_collection = MONGO_CONFIG["OTP_COLLECTION"]["collection_name"]
        self.manager_collection = MONGO_CONFIG["Manager_COLLECTION"]["collection_name"]
        self.admin_collection = MONGO_CONFIG["Admin_COLLECTION"]["collection_name"]
        self.mentor_collection = MONGO_CONFIG["Mentor_COLLECTION"]["collection_name"]
        self.resume_collection = MONGO_CONFIG["Resume_COLLECTION"]["collection_name"]
        self.attendance_collection = MONGO_CONFIG["Attendance"]["collection_name"]
        self.curriculum_collection = MONGO_CONFIG["curriculum"]["collection_name"]
        self.schedule_collection = MONGO_CONFIG["schedule"]["collection_name"]
        self.exam_collection = MONGO_CONFIG["exams"]["collection_name"]
        self.questions_collection = MONGO_CONFIG["questions"]["collection_name"]
        self.batches_collection = MONGO_CONFIG["batches"]["collection_name"]
        self.leave_collection = MONGO_CONFIG["leave_request"]["collection_name"]
        self.DASHBOARDSHEET = config_data["DASHBOARD_GSHEET"]["url"]
        self.DASHBOARD_COLLECTION = config_data["DASHBOARD_GSHEET"]["collection"]
        self.SHEET_NAME = config_data["DASHBOARD_GSHEET"]["sheetname"]


    def add_api(self):
        api = Api(self, catch_all_404s=True)
        api.add_resource(HealthCheck, "/")
        api.add_resource(GoogleSheetReader,"/api/v1/refreshdashboard")
        #admin Apis
        api.add_resource(BdeSignup,  "/api/v1/bdesignup" )
        api.add_resource(ManagerLogin, "/api/v1/manager" )
        api.add_resource(SuperAdmin,"/api/v1/admin")
        api.add_resource(Mentors,"/api/v1/mentor"),
        api.add_resource(PracticeMentors,"/api/v1/practicementor")
        api.add_resource(CurriCulum,"/api/v1/syllabus" )
        api.add_resource(AllAdminsCount, "/api/v1/adminsdata") 
        api.add_resource(Sales,"/api/v2/sales" )
        #Manager apis
        api.add_resource(Add_Student, "/api/v1/addstudent")
        api.add_resource(ScheduleBatches, "/api/v1/schedule")
        api.add_resource(GetScheduledData, "/api/v1/getscheduledata")
        api.add_resource(CreateBatch, "/api/v1/batches")
        api.add_resource(ManagerLeaveupdated, "/api/v1/leaves")
        #mentors apis
        api.add_resource(Mentor_CurriCulum,"/api/v2/mentorsyllabus" )
        api.add_resource(ListofStudentsForMentor, "/api/v1/mentorstds")
        #Attendance apis
        api.add_resource(Attendace,"/api/v1/attend")
        api.add_resource(AttendData,"/api/v1/attendance")
        api.add_resource(AttendCheck,"/api/v1/attendcheck")
        api.add_resource(GetAttendance,"/api/v1/getattends")
        api.add_resource(GetMissingAttendance,"/api/v1/missattends")
        api.add_resource(DownloadAttendance,"/api/v1/downloadattends")
        api.add_resource(GetBatchwiseAttendance,"/api/v1/batchwiseattends")
        #Student apis
        api.add_resource(StudentSignup,"/api/v1/signup")
        api.add_resource(Profile_pic,"/api/v1/pic")
        api.add_resource(GetStudentDetails,"/api/v1/getstudentdetails" )
        api.add_resource(UpdateResume,"/api/v1/updateresume")
        api.add_resource(StudentsCurriculum,"/api/v1/stdcurriculum")
        api.add_resource(StudentLeaveRequest,"/api/v1/stdleave")
        api.add_resource(StudentEligibleJobs,"/api/v1/stdeligiblejobs")
        api.add_resource(Search_Students,"/api/v1/searchstudent" )
        api.add_resource(ATSCheck,"/api/v1/atscheck")
        api.add_resource(GetAllStudents,"/api/v1/allstudents")
        api.add_resource(StudentsByLocation,"/api/v1/stdlocations")
        api.add_resource(Add_zoho_Student,"/api/v1/zohostudent")
        api.add_resource(zoho_Invoice,"/api/v1/zohoinvoice")
        #BDE apis
        api.add_resource(JobPosting, "/api/v1/postjobs")
        api.add_resource(ListOpenings, "/api/v1/listopenings")
        api.add_resource(JobApplication, "/api/v1/applyforjob")
        api.add_resource(GetAppliedJobsList, "/api/v1/getappliedjobslist")
        api.add_resource(DownloadResumes, "/api/v1/downloadresume")
        api.add_resource(GetJobDetails, "/api/v1/getjobdetails")
        api.add_resource(EditJob, "/api/v1/editjob")
        api.add_resource(DownloadAppliedStudentList, "/api/v1/downloadapliedstudents")
        api.add_resource(GetAppliedStudentList,"/api/v1/getappliedstudentslist"  )

        api.add_resource(StudentVerification, "/api/v1/studentotp")
        api.add_resource(ValidateOTP, "/api/v1/verifyotp")        
        api.add_resource(AllResumes, "/api/v1/allresumes")
        api.add_resource(ForgotPwd, "/api/v1/forgotpassword")
        api.add_resource(Updatepassword, "/api/v1/updatepassword")
        api.add_resource(Logins, "/api/v1/login")
        api.add_resource(UpdateJobApplicants,"/api/v1/updatejobapplicants")
        #related
        api.add_resource(RefreshToken, "/api/v1/refresh")
        api.add_resource(Logout, "/api/v1/logout")
        api.add_resource(CodeGnan,   "/api/v1/codegnan" )
        api.add_resource(EducationalBranches,  "/api/v1/allbranches"),
        api.add_resource(Skills, "/api/v1/skills")
        api.add_resource(Locations, "/api/v1/location")
        api.add_resource(TechStack, "/api/v1/techstack")
        api.add_resource(Designation, "/api/v1/designation")
        api.add_resource(Subjects, "/api/v1/subjects")
        api.add_resource(Selected_Stutents_list, "/api/v2/selected-list")
        api.add_resource(InterviewRounds, "/api/v2/interview-rounds")
        api.add_resource(DownloadAllStudents, "/api/v2/download-all-students")
        api.add_resource(Student_Rounds, "/api/v2/student-rounds")
        api.add_resource(Certificates, "/api/v2/certificates")
        api.add_resource(Dowload_certificates, "/api/v2/download-certificates")
        # -------------- Exam APIs -------------#
        # Examiner Exam APIs
        api.add_resource(CheckExamStatus, "/api/v3/check-exam-status") 
        api.add_resource(GetExamData, "/api/v3/get-exam-data") 
        api.add_resource(GenerateExamPaper, "/api/v3/generate-exam-paper")
        api.add_resource(ExaminerExamDayList, "/api/v3/exam-day-list")
        api.add_resource(ExaminerBatchReports, "/api/v3/exam-batch-reports")

        # Student Exam APIs
        api.add_resource(GetAvailableExams, "/api/v3/get-available-exams")
        api.add_resource(StartExam, "/api/v3/startexam")
        api.add_resource(CodeExecution, "/api/v3/code-execution")
        api.add_resource(SubmitExam, "/api/v3/submit-exam")
        api.add_resource(ExamQuestionReview, "/api/v3/exam-questions-review")
        api.add_resource(StudentExamSummary, "/api/v3/student-exam-summary")
        api.add_resource(StudentExamDetail, "/api/v3/student-exam-detail")
        api.add_resource(ExamBatchLeaderboard, "/api/v3/exam-batch-leaderboard")
        api.add_resource(GetConductedExamDates, "/api/v3/get-conducted-exam-dates")

        # Mentor Exam APIs
        api.add_resource(MentorExamDayList, "/api/v3/mentor-exam-day-list")
        
        # Interview APIs
        api.add_resource(GetInterviewData, "/api/v3/interview-data")

        # Admin Window Configuration APIs
        api.add_resource(WindowConfigResource, "/api/v3/admin/window-config")
        api.add_resource(WindowConfigDetailResource, "/api/v3/admin/window-config/<string:exam_type>")
        
        # Admin Exam Toggle APIs
        api.add_resource(ExamToggleResource, "/api/v3/admin/exam-toggle")
        api.add_resource(ExamToggleDetailResource, "/api/v3/admin/exam-toggle/<string:exam_type>")

        #Testing
        api.add_resource(TesterAPI,"/api/v2/tester")
        api.add_resource(SubjectsAPI, "/api/v2/tester-subjects")
        api.add_resource(UploadAPI, "/api/v2/test-upload-questions")
        api.add_resource(QuestionAPI, "/api/v2/question-crud")
        api.add_resource(CurriculumAPI, "/api/v2/tester-curriculum")
        api.add_resource(VerificationAPI, "/api/v2/verify-question")
        api.add_resource(SubmissionAPI, "/api/v2/test-submission")
        api.add_resource(TesterOverallAPI, "/api/v2/testers-overall")
        api.add_resource(TesterByIdAPI, "/api/v2/tester/<string:intern_id>")
        api.add_resource(TesterSubjectDetailsAPI, "/api/v2/tester/<string:intern_id>/subject/<string:subject>")
        api.add_resource(DumpAPI, "/api/v2/dump-questions")
        api.add_resource(ExecutionAPI, "/api/v2/run-code")
        
        #Active Batches
        api.add_resource(ActiveBatches, "/api/v1/active-batches")
        # -------------- Code Playground APIs -------------
        # Code playground features with feature flag middleware
        api.add_resource(create_feature_aware_resource(cpcurriculum), "/api/v1/cpcurriculum")       
        api.add_resource(create_feature_aware_resource(QuestionExecution), "/api/v1/question-execution")
        api.add_resource(create_feature_aware_resource(CpSubmissions), "/api/v1/test-cpsubmissions")
        api.add_resource(create_feature_aware_resource(CpProgress), "/api/v1/cp-progress")
        api.add_resource(create_feature_aware_resource(QuestionsWithProgress), "/api/v1/questions-with-progress")
        api.add_resource(create_feature_aware_resource(GetFirstSubject), "/api/v1/get-first-subject")      
        api.add_resource(CodePlaygroundFeatureCheck, "/api/v1/codeplayground-feature-check")
        
        # -------------- Feature‑flag admin endpoints -------------
        api.add_resource(FeatureToggle,"/api/v1/flags",# list all flags  (GET)
                         "/api/v1/flags/<string:key>") # get/post single flag
        
        # Location-based 
        api.add_resource(LocationFeatureToggle,
                         "/api/v1/location-flags",  # list all location flags (GET)
                         "/api/v1/location-flags/<string:location>",  # get flags for location (GET)
                         "/api/v1/location-flags/<string:location>/<string:flag_name>")  # get/post specific flag (GET/POST)
        
        # Batch-based 
        api.add_resource(BatchFeatureToggle,
                         "/api/v1/batch-flags",
                         "/api/v1/batch-flags/<string:batch>",
                         "/api/v1/batch-flags/<string:batch>/<string:flag_name>")
        
        # Hierarchical 
        api.add_resource(HierarchicalFeatureView,
                         "/api/v1/feature-hierarchy",
                         "/api/v1/feature-hierarchy/<string:flag_name>")
        
        api.add_resource(Leaderboard, "/api/v1/leaderboard")

         # MySQL Templates
        api.add_resource(TemplateUpload, '/api/v1/mysql-template-upload')
        api.add_resource(TemplateList, '/api/v1/mysql-templates')
        api.add_resource(TemplateTableNames, '/api/v1/mysql-template-tables/<string:template_id>')
        api.add_resource(TemplateTableData, '/api/v1/mysql-template-table/<string:template_id>/<string:table_names>')
        # -------------- Whatsapp APIs -------------
        # Whatsapp Notify Reports
        api.add_resource(ExamReport, "/api/v1/exam-report")
        api.add_resource(BatchReport, "/api/v1/batch-report")

        # Parent Whatsapp Report APIs
        api.add_resource(ReportProcessorAPI, '/api/v1/reports-process')
        api.add_resource(WhatsAppAPI, '/api/v1/whatsapp')
        api.add_resource(TaskStatusAPI, '/api/v1/reports-status/<string:task_id>')
        api.add_resource(PeriodAPI, '/api/v1/reports-periods')

        # Whatsapp Webhook Status Fetch APIs
        api.add_resource(WaParentStatusDelivery, "/api/v1/wa-parent-status-delivery") #Main
        api.add_resource(WaDailyExamDelivery, "/api/v1/wa-daily-exam-delivery") 

app = MyFlask(__name__)
# Configure JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES')))
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS')))
jwt = JWTManager(app)

# Initialize API routes
app.add_api()
CORS(app,supports_credentials=True)

if __name__ == '__main__':
    app.run()