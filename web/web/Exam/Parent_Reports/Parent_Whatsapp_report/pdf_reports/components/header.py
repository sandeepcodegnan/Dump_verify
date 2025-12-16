from reportlab.lib import colors
from reportlab.lib.units import inch

def draw_header(canvas, doc, title="Weekly Report"):
    header_height = 0.5 * inch
    x = doc.leftMargin
    y = doc.height + doc.bottomMargin - header_height

    # shadow
    canvas.saveState()
    canvas.setFillColor(colors.black)
    try:
        canvas.setFillAlpha(0.1)
    except AttributeError:
        pass
    canvas.roundRect(x+1, y-1, doc.width, header_height, 5, fill=1, stroke=0)
    canvas.restoreState()

    # white bg
    canvas.setFillColor(colors.white)
    canvas.roundRect(x, y, doc.width, header_height, 5, fill=1, stroke=0)

    # left logo text
    canvas.setFont("Helvetica-Bold", 15)
    text_y = y + (header_height - 15)/2 + 2
    text_x = x + 6
    canvas.setFillColor(colors.HexColor("#001c80"))
    canvas.drawString(text_x, text_y, "Code")
    w = canvas.stringWidth("Code", "Helvetica-Bold", 15)
    canvas.setFillColor(colors.red)
    canvas.drawString(text_x + w, text_y, "gnan")
    
    # title from parameter
    canvas.setFont("Helvetica-Bold", 15)
    canvas.setFillColor(colors.HexColor("#001c80"))
    canvas.drawRightString(x + doc.width - 6, text_y, title)