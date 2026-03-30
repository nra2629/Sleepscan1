"""
utils/report.py
Generates PDF report using ReportLab.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.graphics.shapes import Drawing, Rect, String
import io, base64
from datetime import datetime

NAVY   = colors.HexColor('#1a1a2e')
PAPER  = colors.HexColor('#f7f4ef')
DIM    = colors.HexColor('#8a8070')
BORDER = colors.HexColor('#e0dbd0')
WARN   = colors.HexColor('#b5451b')
GOOD   = colors.HexColor('#2d6a4f')
OK     = colors.HexColor('#1a4d6b')
WHITE  = colors.white
BLACK  = colors.HexColor('#0d1117')

W, H   = A4
MARGIN = 18 * mm

STAGE_COLORS_HEX = {
    'W': '#c8c0f8', 'N1': '#a8d4ff',
    'N2': '#6aabee', 'N3': '#2a50b4', 'REM': '#c890e8'
}


def ps(name, size, color=BLACK, bold=False, align=TA_LEFT, leading=None):
    return ParagraphStyle(name, fontName='Helvetica-Bold' if bold else 'Helvetica',
                          fontSize=size, textColor=color,
                          alignment=align, leading=leading or size*1.35)


def b64_to_image(b64_str, width, height):
    """Convert base64 PNG to ReportLab Image."""
    img_data = base64.b64decode(b64_str)
    buf = io.BytesIO(img_data)
    return Image(buf, width=width, height=height)


def generate_pdf(data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=MARGIN, bottomMargin=MARGIN)

    pid        = data.get('patient_id', 'Unknown')
    night      = data.get('night', 'Night 1')
    age        = data.get('age', '')
    gender     = data.get('gender', '')
    tech       = data.get('technologist', '')
    clinic     = data.get('clinic', '')
    cluster    = data.get('cluster_name', '')
    cluster_id = data.get('cluster_id', 0)
    c_desc     = data.get('cluster_desc', {})
    var        = data.get('var_insight', {})
    metrics    = data.get('metrics', {})
    hypno_img  = data.get('hypno_img', None)
    signal_img = data.get('signal_img', None)
    date_str   = datetime.today().strftime('%d %b %Y')

    content_w = W - 2 * MARGIN
    story = []

    # ── HEADER ───────────────────────────────────
    d = Drawing(content_w, 26*mm)
    d.add(Rect(0, 0, content_w, 26*mm, fillColor=NAVY, strokeColor=NAVY))
    d.add(String(5*mm, 18*mm, f'Patient {pid} · {night}' + (f' · Age {age}' if age else '') + (f' · {gender.title()}' if gender else ''),
                 fontName='Helvetica-Bold', fontSize=15, fillColor=WHITE))
    d.add(String(5*mm, 11*mm, f'Generated {date_str}  ·  {clinic}  ·  {tech}',
                 fontName='Helvetica', fontSize=8, fillColor=colors.HexColor('#888888')))
    d.add(String(5*mm, 5*mm, f'Cluster: {cluster}  ·  {c_desc.get("label", "")}',
                 fontName='Helvetica', fontSize=8, fillColor=colors.HexColor('#7ab8ff')))
    story.append(d)
    story.append(Spacer(1, 5*mm))

    # ── METRICS ──────────────────────────────────
    eff   = metrics.get('efficiency', 0)
    trans = metrics.get('transitions', 0)
    n3    = metrics.get('n3_pct', 0)
    rem   = metrics.get('rem_pct', 0)
    tst   = metrics.get('tst_hours', 0)

    def metric_cell(label, val, sub, col):
        return [Paragraph(label.upper(), ps('ml',6,DIM)),
                Paragraph(str(val), ps('mv',18,col,bold=True)),
                Paragraph(sub, ps('ms',7,DIM,leading=9))]

    cw = content_w / 5 - 2*mm
    metrics_table = Table([[
        metric_cell('Sleep efficiency', f'{eff}%',  'Typical ≥85%',   WARN if eff<85 else GOOD),
        metric_cell('Transitions',      trans,       'Typical 150–200', WARN if trans>200 else GOOD),
        metric_cell('Deep sleep N3',    f'{n3}%',   'Typical 15–25%', WARN if n3<15 else GOOD),
        metric_cell('REM sleep',        f'{rem}%',  'Typical 20–25%', WARN if rem<18 else GOOD),
        metric_cell('Total sleep',      f'{tst}h',  'Time asleep',    OK),
    ]], colWidths=[cw]*5)
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),WHITE),
        ('BOX',(0,0),(-1,-1),.5,BORDER),
        ('INNERGRID',(0,0),(-1,-1),.5,BORDER),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 5*mm))

    # ── HYPNOGRAM ────────────────────────────────
    story.append(Paragraph('HYPNOGRAM · FULL NIGHT · 30-SECOND EPOCHS', ps('sl',7,DIM)))
    story.append(Spacer(1, 2*mm))
    if hypno_img:
        story.append(b64_to_image(hypno_img, content_w, 60*mm))
    story.append(Spacer(1, 5*mm))

    # ── RAW SIGNALS ──────────────────────────────
    if signal_img:
        story.append(Paragraph('RAW PSG SIGNALS · FIRST 10 MINUTES', ps('sl',7,DIM)))
        story.append(Spacer(1, 2*mm))
        story.append(b64_to_image(signal_img, content_w, 55*mm))
        story.append(Spacer(1, 5*mm))

    # ── CLUSTER + VAR SIDE BY SIDE ───────────────
    story.append(HRFlowable(width='100%', thickness=.5, color=BORDER))
    story.append(Spacer(1, 4*mm))

    half = (content_w - 5*mm) / 2

    # Build bullet list for sleep profile
    bullets = c_desc.get('bullets', [])
    bullet_items = [Paragraph('SLEEP TYPE PROFILE', ps('cl',7,DIM,bold=True)), Spacer(1,3*mm)]
    for b in bullets:
        bullet_items.append(Paragraph(f'• {b}', ps('cd',8,BLACK,leading=13)))
        bullet_items.append(Spacer(1,1*mm))
    cluster_content = bullet_items

    # VAR insight — use new insight field
    var_content = [
        Paragraph('BRAIN SIGNAL BEHAVIOUR', ps('vl',7,DIM,bold=True)),
        Spacer(1,3*mm),
        Paragraph(var.get('insight', var.get('meaning','')), ps('vm',8,BLACK,leading=13)),
        Spacer(1,3*mm),
        Paragraph(f'EEG persistence: {var.get("eeg_persistence",0):.3f}   EOG persistence: {var.get("eog_persistence",0):.3f}   EMG persistence: {var.get("emg_persistence",0):.3f}', ps('vc',7,DIM)),
    ]

    two_col = Table([[cluster_content, var_content]], colWidths=[half, half])
    two_col.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),
        ('RIGHTPADDING',(0,0),(0,0),8*mm),
        ('TOPPADDING',(0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 5*mm))

    # ── FOOTER ───────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=.5, color=BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f'SleepScan Clinical Report · {clinic} · {tech} · {date_str} · '
        'This report is generated automatically and should be reviewed by a qualified sleep technologist.',
        ps('ft',6,DIM,align=TA_CENTER)))

    doc.build(story)
    return buf.getvalue()
