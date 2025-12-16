from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import student_required
import PyPDF2
import docx
import requests
from web.db.db_utils import get_collection

resume_collection = get_collection('ats_check')
student_collection = get_collection('students')

API_BASE = "https://openwebui.scubey.com"
API_KEY = "sk-53776ea374fb499b96c73b9640c4326a"

def extract_text_from_file(file):
    text = ''
    if file.filename.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    elif file.filename.endswith('.docx'):
        doc = docx.Document(file)
        text = '\n'.join([p.text for p in doc.paragraphs])
    else:
        raise ValueError("Unsupported file format. Please upload a .pdf or .docx file.")

    # Count the number of words
    word_count = len(text.split())
    return text, word_count

def analyze_resume_with_llm(resume_text):
    """Use OpenWebUI API to analyze resume text for ATS scoring and feedback."""
    prompt = f"""
    You are an ATS scoring assistant. Critically evaluate the following resume for a professional role. Provide the following:
    1. Extracted Skills: List all skills found in the resume as a comma-separated list.
    2. Missing Skills: List all relevant skills missing from the resume as a comma-separated list.
    3. ATS Score: Provide a numeric score (0-100) reflecting the resume's quality and relevance.
    4. Feedback: Provide actionable suggestions for improvement under these categories:
       - Skills,SKILLS,Technical Skills
       - Sections
       - Formatting
       - projects Minimum 2
       - certifications minimum 2
       - strengths minimum 3
       - hobbies minimum 3
       - languages known minimum 3
       - linkedin url
       - GitHub url
    Use this format:
    - Extracted Skills: skill1, skill2, skill3, etc.
    - Missing Skills: skill1, skill2, skill3, etc.
    - ATS Score: XX.XX
    - Feedback:
       - Skills,SKILLS,Technical Skills: <feedback>
       - Sections: <feedback>
       - Formatting: <feedback>
    Resume content:
    {resume_text}
    """

    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama3.1:latest",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.1,
            "seed": hash(resume_text[:100]) % 1000
        }
        
        response = requests.post(f"{API_BASE}/api/chat/completions", headers=headers, json=data)
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
        else:
            return None, [], [], {"Error": f"API Error: {response.status_code} - {response.text}"}

        ats_score = None
        extracted_skills = []
        missing_skills = []
        feedback_sections = {"Skills": "", "Sections": "", "Formatting": ""}

        import re
        
        # Parse with multiple strategies
        lines = content.splitlines()
        content_lower = content.lower()
        
        # Strategy 1: Line by line parsing
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            if "ats score" in line_lower and ":" in line:
                score_match = re.search(r'(\d+\.?\d*)', line)
                if score_match:
                    ats_score = round(float(score_match.group(1)), 2)
            
            elif "extracted skills" in line_lower and ":" in line:
                skills_text = line.split(":", 1)[1].strip()
                if skills_text and skills_text.lower() not in ['none', 'n/a', 'not found']:
                    extracted_skills = [skill.strip() for skill in skills_text.split(",") if skill.strip()]
            
            elif "missing skills" in line_lower and ":" in line:
                skills_text = line.split(":", 1)[1].strip()
                if skills_text and skills_text.lower() not in ['none', 'n/a', 'not found']:
                    missing_skills = [skill.strip() for skill in skills_text.split(",") if skill.strip()]
        
        # Strategy 2: Block parsing for feedback
        feedback_block = ""
        if "feedback:" in content_lower:
            feedback_start = content_lower.find("feedback:")
            feedback_block = content[feedback_start:]
        
        # Extract feedback sections with regex
        skills_feedback = re.search(r'-\s*skills?:\s*([^\n-]+(?:\n(?!\s*-)[^\n]*)*)', feedback_block, re.IGNORECASE | re.MULTILINE)
        sections_feedback = re.search(r'-\s*sections?:\s*([^\n-]+(?:\n(?!\s*-)[^\n]*)*)', feedback_block, re.IGNORECASE | re.MULTILINE)
        formatting_feedback = re.search(r'-\s*formatting:\s*([^\n-]+(?:\n(?!\s*-)[^\n]*)*)', feedback_block, re.IGNORECASE | re.MULTILINE)
        
        if skills_feedback:
            feedback_sections["Skills"] = skills_feedback.group(1).strip()
        if sections_feedback:
            feedback_sections["Sections"] = sections_feedback.group(1).strip()
        if formatting_feedback:
            feedback_sections["Formatting"] = formatting_feedback.group(1).strip()

        # Ensure we have valid data
        if ats_score is None:
            ats_score = 65.0
        
        if not extracted_skills:
            # skill extraction
            skill_patterns = r'\b(Python|Java|JavaScript|React|Node|Flask|Django|AWS|Git|SQL|MongoDB|Docker|Jenkins|HTML|CSS|C\+\+|C#|Go|Rust|Kotlin|Swift|PHP|Ruby|Angular|Vue|Spring|Express|PostgreSQL|MySQL|Redis|Kubernetes|Linux|Ubuntu|Machine Learning|AI|Data Science|DevOps|CI/CD)\b'
            extracted_skills = list(set(re.findall(skill_patterns, resume_text, re.IGNORECASE)))
        
        if not missing_skills:
            def generate_smart_missing_skills():
                extracted_lower = [s.lower() for s in extracted_skills]
                suggestions = []
                
                # Smart suggestions based on existing skills (deterministic order)
                skill_map = {
                    'python': ['Django', 'FastAPI', 'Pandas', 'NumPy'],
                    'java': ['Spring Boot', 'Maven', 'Hibernate', 'JUnit'],
                    'javascript': ['TypeScript', 'Node.js', 'Webpack', 'Jest'],
                    'react': ['Redux', 'Next.js', 'React Testing Library'],
                    'node': ['Express.js', 'NestJS', 'Socket.io'],
                    'sql': ['PostgreSQL', 'Query Optimization', 'Database Design'],
                    'html': ['CSS3', 'Sass/SCSS', 'Bootstrap'],
                    'git': ['GitHub Actions', 'GitLab CI', 'Version Control']
                }
                
                # Add complementary skills in consistent order
                for skill in sorted(extracted_lower):
                    if skill in skill_map:
                        for complement in skill_map[skill]:
                            if complement.lower() not in extracted_lower and complement not in suggestions and len(suggestions) < 6:
                                suggestions.append(complement)
                
                # Add trending skills if space available (consistent order)
                trending = ['System Design', 'API Development', 'Testing Frameworks', 'Docker', 'Kubernetes', 'AWS']
                for skill in trending:
                    if skill.lower() not in extracted_lower and skill not in suggestions and len(suggestions) < 6:
                        suggestions.append(skill)
                
                return suggestions[:6] if suggestions else ['System Design', 'Testing', 'API Development']
            
            missing_skills = generate_smart_missing_skills()
        
        # Generate dynamic feedback based on resume analysis
        def generate_dynamic_feedback():
            resume_lower = resume_text.lower()
            
            # Skills feedback
            if not feedback_sections["Skills"]:
                skill_count = len(extracted_skills)
                missing_count = len(missing_skills)
                
                if skill_count >= 12:
                    feedback_sections["Skills"] = f"Excellent {skill_count} skills identified. Consider highlighting expertise levels for key technologies."
                elif skill_count >= 8:
                    feedback_sections["Skills"] = f"Good {skill_count} technical skills. Add {min(3, missing_count)} trending technologies to stay competitive."
                elif skill_count >= 4:
                    feedback_sections["Skills"] = f"Moderate {skill_count} skills shown. Expand with {min(5, missing_count)} additional technologies from job requirements."
                else:
                    feedback_sections["Skills"] = f"Only {skill_count} skills detected. Add 6-8 relevant technical skills to improve ATS matching."
            
            # Sections feedback
            if not feedback_sections["Sections"]:
                word_count = len(resume_text.split())
                has_projects = any(keyword in resume_lower for keyword in ['project', 'built', 'developed', 'created'])
                has_experience = any(keyword in resume_lower for keyword in ['experience', 'worked', 'internship', 'job'])
                
                if word_count > 400 and has_projects and has_experience:
                    feedback_sections["Sections"] = "Comprehensive resume with strong project and experience sections. Consider quantifying achievements."
                elif word_count > 250:
                    if not has_projects:
                        feedback_sections["Sections"] = "Add a dedicated Projects section showcasing 2-3 technical projects with technologies used."
                    elif not has_experience:
                        feedback_sections["Sections"] = "Include internships, part-time work, or volunteer experience to demonstrate practical application."
                    else:
                        feedback_sections["Sections"] = "Good structure. Add metrics and quantifiable results to strengthen impact."
                else:
                    feedback_sections["Sections"] = f"Resume too brief ({word_count} words). Expand with detailed project descriptions and technical achievements."
            
            # Formatting feedback
            if not feedback_sections["Formatting"]:
                has_bullets = '•' in resume_text or '-' in resume_text
                has_sections = len([line for line in resume_text.split('\n') if line.isupper() or any(header in line.lower() for header in ['education', 'experience', 'skills', 'projects'])]) >= 3
                
                if has_bullets and has_sections:
                    feedback_sections["Formatting"] = "Well-structured with clear sections and bullet points. Ensure consistent font and spacing."
                elif has_sections:
                    feedback_sections["Formatting"] = "Good section organization. Use bullet points for better readability and ATS parsing."
                else:
                    feedback_sections["Formatting"] = "Improve structure with clear section headers (Education, Skills, Projects, Experience) and bullet points."
        
        generate_dynamic_feedback()

        return ats_score, extracted_skills, missing_skills, feedback_sections
    except Exception as e:
        return 50.0, [], ["System Design", "Testing", "API Development"], {"Skills": "Analysis error occurred", "Sections": "Analysis error occurred", "Formatting": "Analysis error occurred"}


class ATSCheck(Resource):
    def __init__(self):
        super().__init__()
        self.collection = student_collection
        self.res_collection = resume_collection

    def post(self):
        file = request.files.get('resume')
        std_id = request.form.get('student_id')
        
        if not file or file.filename == '':
            return {"error": "No file selected."}, 400
            
        students = student_collection.find_one({"studentId": std_id})
        if not students:
            return {"error": "Student not found"}, 404
            
        batch = students.get("BatchNo")
        location = students.get("location")
        
        from datetime import datetime
        try:
            resume_text, word_count = extract_text_from_file(file)
            ats_score, extracted_skills, suggesting_skills, feedback_sections = analyze_resume_with_llm(resume_text)

            resume_data = {
                "std_Id": std_id,
                "ats_score": ats_score,
                "word_count": word_count
            }

            # Remove existing resume for this student
            self.res_collection.update_one(
                {"batch": batch, "location": location},
                {"$pull": {"Resumes": {"std_Id": std_id}}}
            )
            
            # Add new resume data
            self.res_collection.update_one(
                {"batch": batch, "location": location},
                {"$setOnInsert": {"batch": batch, "location": location},
                 "$push": {"Resumes": resume_data}},
                upsert=True
            )

            return {
                "ats_score": ats_score,
                "extracted_skills": extracted_skills,
                "suggesting_skills": suggesting_skills,
                "feedback_sections": feedback_sections,
                "word_count": word_count
            }, 200
        except Exception as e:
            return {"error": f"Processing failed: {str(e)}"}, 500
        
    @student_required
    def get(self):
        id = request.args.get('student_id')

        if not id:
            return {"error": "Missing required data"}, 400  

        batch_doc = self.res_collection.find_one({"Resumes.std_Id": id})
        if not batch_doc:
            return {"error": "No resume found for the given student_id"}, 404

        resume = next((r for r in batch_doc["Resumes"] if r["std_Id"] == id), None)
        
        data = {
            "ats_score": resume.get("ats_score"),
            "word_count": resume.get("word_count")
        }

        return {"message": "Resume Data found", "Resume_score": data}, 200