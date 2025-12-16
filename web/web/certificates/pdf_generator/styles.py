from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

_CACHED_STYLES = None

def get_styles():
    global _CACHED_STYLES
    if _CACHED_STYLES is None:
        styles = getSampleStyleSheet()
        
        # Certificate Title Style (matching DOCX)
        styles.add(ParagraphStyle(
            name='CertificateTitle',
            fontSize=12,
            leading=16,
            textColor=colors.black,
            fontName='Times-Bold',
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        # Date Style (matching DOCX - top right)
        styles.add(ParagraphStyle(
            name='DateStyle',
            fontSize=12,
            leading=16,
            textColor=colors.black,
            fontName='Times-Bold',
            alignment=TA_RIGHT
        ))
        
        # Main Content Style (matching DOCX - justified text)
        styles.add(ParagraphStyle(
            name='MainContent',
            fontSize=12,
            leading=16,
            textColor=colors.black,
            fontName='Times-Roman',
            alignment=TA_JUSTIFY,
            spaceAfter=12
        ))
        
        # Signature Text Style (matching DOCX)
        styles.add(ParagraphStyle(
            name='SignatureText',
            fontSize=12,
            leading=16,
            textColor=colors.black,
            fontName='Times-Roman',
            alignment=TA_LEFT
        ))
        
        # Signature Name Style (matching DOCX)
        styles.add(ParagraphStyle(
            name='SignatureName',
            fontSize=12,
            leading=16,
            textColor=colors.black,
            fontName='Times-Roman',
            alignment=TA_LEFT
        ))
        
        # Signature Title Style (matching DOCX)
        styles.add(ParagraphStyle(
            name='SignatureTitle',
            fontSize=12,
            leading=16,
            textColor=colors.black,
            fontName='Times-Roman',
            alignment=TA_LEFT
        ))
        
        # Footer Style
        styles.add(ParagraphStyle(
            name='Footer',
            fontSize=12,
            leading=16,
            textColor=colors.black,
            fontName='Times-Roman',
            alignment=TA_CENTER
        ))
        
        _CACHED_STYLES = styles
    return _CACHED_STYLES