"""Repository Factory - DRY Implementation"""
from typing import Dict
from web.Exam.Daily_Exam.repositories.exam.exam_repo import ExamRepo
from web.Exam.Daily_Exam.repositories.exam.optimized_exam_repo import OptimizedExamRepo
from web.Exam.Daily_Exam.repositories.student.student_repo import StudentRepo
from web.Exam.Daily_Exam.repositories.question.question_repo import QuestionRepo
from web.Exam.Daily_Exam.repositories.curriculum.curriculum_repo import CurriculumRepo

class RepositoryFactory:
    """Centralized repository creation (DRY principle)"""
    
    _exam_repos: Dict[str, ExamRepo] = {}
    _optimized_exam_repos: Dict[str, OptimizedExamRepo] = {}
    _question_repos: Dict[str, QuestionRepo] = {}
    
    @classmethod
    def get_exam_repo(cls, collection_name: str) -> ExamRepo:
        """Get or create exam repository instance"""
        if collection_name not in cls._exam_repos:
            cls._exam_repos[collection_name] = ExamRepo(collection_name)
        return cls._exam_repos[collection_name]
    
    @classmethod
    def get_optimized_exam_repo(cls, collection_name: str) -> OptimizedExamRepo:
        """Get or create optimized exam repository instance for Weekly/Monthly exams"""
        if collection_name not in cls._optimized_exam_repos:
            cls._optimized_exam_repos[collection_name] = OptimizedExamRepo(collection_name)
        return cls._optimized_exam_repos[collection_name]
    
    @classmethod
    def get_student_repo(cls) -> StudentRepo:
        """Get student repository instance with caching"""
        if not hasattr(cls, '_student_repo'):
            cls._student_repo = StudentRepo()
        return cls._student_repo
    
    @classmethod
    def get_question_repo(cls, subject: str) -> QuestionRepo:
        """Get or create question repository instance"""
        if subject not in cls._question_repos:
            cls._question_repos[subject] = QuestionRepo(subject)
        return cls._question_repos[subject]
    
    @classmethod
    def get_curriculum_repo(cls) -> CurriculumRepo:
        """Get curriculum repository instance"""
        return CurriculumRepo()
    
    # window config repo
    @classmethod 
    def get_window_config_repo(cls):
        """Get window configuration repository instance"""
        from web.Exam.Daily_Exam.repositories.admin.window_config_repo import WindowConfigRepo
        if not hasattr(cls, '_window_config_repo'):
            cls._window_config_repo = WindowConfigRepo()
        return cls._window_config_repo
    
    # exam toggle repo
    @classmethod
    def get_exam_toggle_repo(cls):
        """Get exam toggle repository instance"""
        from web.Exam.Daily_Exam.repositories.admin.exam_toggle_repo import ExamToggleRepo
        if not hasattr(cls, '_exam_toggle_repo'):
            cls._exam_toggle_repo = ExamToggleRepo()
        return cls._exam_toggle_repo
