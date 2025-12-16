"""Image Service - Handles student profile images"""
from typing import Optional
from abc import ABC, abstractmethod

class ImageProvider(ABC):
    """Abstract image provider interface (DIP)"""
    
    @abstractmethod
    def get_image_url(self, student_id: str) -> Optional[str]:
        """Get image URL for student"""
        pass

class GridFSImageProvider(ImageProvider):
    """GridFS implementation of image provider"""
    
    def __init__(self, fs):
        self.fs = fs
    
    def get_image_url(self, student_id: str) -> Optional[str]:
        """Get image URL from GridFS"""
        if not student_id:
            return None
        
        try:
            pic = self.fs.find_one({'filename': student_id})
            if pic:
                return f"/api/v1/pic?student_id={student_id}"
        except (FileNotFoundError, ValueError, TypeError):
            pass
        
        return None

class ImageService:
    """Service for handling student images"""
    
    def __init__(self, image_provider: ImageProvider):
        self.image_provider = image_provider
    
    def get_student_image_url(self, student_id: str) -> Optional[str]:
        """Get student profile image URL"""
        return self.image_provider.get_image_url(student_id)