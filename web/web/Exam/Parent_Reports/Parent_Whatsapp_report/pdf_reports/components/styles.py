from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

_CACHED_STYLES = None

def get_styles():
    global _CACHED_STYLES
    if _CACHED_STYLES is None:
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='InfoLabel', fontSize=12, leading=14,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='InfoValue', fontSize=12, leading=14,
            textColor=colors.black,
            fontName='Helvetica'
        ))
        styles.add(ParagraphStyle(
            name='SectionTitle', fontSize=16, leading=20,
            textColor=colors.HexColor('#001c80'),
            fontName='Helvetica-Bold',
            spaceAfter=8
        ))
        styles.add(ParagraphStyle(
            name='TableHeader', fontSize=10, leading=12,
            alignment=TA_CENTER,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='TableBodyLeft', fontSize=10, leading=12,
            alignment=TA_LEFT,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='CellCenter', 
            fontSize=10, leading=12,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='CenteredTitle',
            fontSize=18, leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#001c80'),
            fontName='Helvetica-Bold',
            spaceAfter=12
        ))
        _CACHED_STYLES = styles
    return _CACHED_STYLES