from celery_app import app
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

os.environ.setdefault('MPLBACKEND', 'Agg')

import psycopg2

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)

import matplotlib.pyplot as plt
import numpy as np


CERTIFICATE_DIR = os.environ.get('CERTIFICATE_DIR', '/certificates')

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'postgres'),
    'port': os.environ.get('DB_PORT', '5432'),
    'dbname': os.environ.get('DB_NAME', 'app_db'),
    'user': os.environ.get('DB_USER', 'app_user'),
    'password': os.environ.get('DB_PASSWORD'),
}

SCORE_LABELS = {
    'web': 'Web Security',
    'pwn': 'Pwn',
    'crypto': 'Cryptography',
    'reverse': 'Reverse Engineering',
    'forensics': 'Forensics',
}


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
#
# ReportLab cannot embed the CFF outlines used by Debian's Noto CJK TTC.
# Use a Unicode CID font for Traditional Chinese and DejaVu Sans for Latin
# text. This avoids the previous fallback that silently used a Latin-only
# font for Chinese.
#

try:
    pdfmetrics.registerFont(UnicodeCIDFont('MSung-Light'))
except Exception:
    pass

_FONT_CANDIDATES = [
    ('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
]

for font_name, font_path in _FONT_CANDIDATES:
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception:
            pass

REGISTERED_FONTS = pdfmetrics.getRegisteredFontNames()

REGULAR_FONT = 'DejaVuSans' if 'DejaVuSans' in REGISTERED_FONTS else 'Helvetica'
BOLD_FONT = 'DejaVuSans-Bold' if 'DejaVuSans-Bold' in REGISTERED_FONTS else 'Helvetica-Bold'
CJK_FONT = 'MSung-Light' if 'MSung-Light' in REGISTERED_FONTS else REGULAR_FONT


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _db_connection():
    return psycopg2.connect(**DB_CONFIG)


def _safe_filename(value):
    value = re.sub(r'[^A-Za-z0-9_.-]+', '_', value or 'student')
    return value[:80] or 'student'


def _update_certificate(certificate_id, status, file_name=None):
    with _db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE certificates
                SET
                    status = %s,
                    file_name = COALESCE(%s, file_name),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, file_name, certificate_id),
            )


def _get_current_display_name(user_id, fallback):
    with _db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT display_name, username FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()

            if not row:
                return fallback

            display_name, username = row
            return display_name or username or fallback


# ---------------------------------------------------------------------------
# Radar chart
# ---------------------------------------------------------------------------

def _build_radar_chart(scores, output_path):
    labels = list(SCORE_LABELS.keys())
    values = [float(scores[k]) for k in labels]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()

    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5.2, 5.2), subplot_kw={'polar': True})

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([SCORE_LABELS[k] for k in labels], fontsize=9)

    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.18)

    ax.set_title('Skill Assessment', pad=18)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Certificate generation
# ---------------------------------------------------------------------------

@app.task(name='tasks.generate_certificate')
def generate_certificate(student_data: dict) -> dict:
    certificate_id = int(student_data['certificate_id'])

    os.makedirs(CERTIFICATE_DIR, exist_ok=True)

    chart_path = os.path.join(CERTIFICATE_DIR, f'.chart_{certificate_id}.png')

    file_name = f"certificate_{certificate_id}_{_safe_filename(student_data.get('username'))}.pdf"
    output_path = os.path.join(CERTIFICATE_DIR, file_name)

    try:
        # Always read the latest Display Name when the worker starts.
        # This prevents a queued job from producing a certificate with
        # an old profile name.
        student_name = _get_current_display_name(
            int(student_data['user_id']),
            student_data.get('name', '學員'),
        )

        _build_radar_chart(student_data['scores'], chart_path)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=48,
            leftMargin=48,
            topMargin=48,
            bottomMargin=48,
        )

        styles = getSampleStyleSheet()

        title = ParagraphStyle(
            'CertificateTitle',
            parent=styles['Title'],
            fontName=BOLD_FONT,
            fontSize=25,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=12,
        )

        subtitle = ParagraphStyle(
            'CertificateSubtitle',
            parent=styles['Normal'],
            fontName=CJK_FONT,
            fontSize=15,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=18,
        )

        centered = ParagraphStyle(
            'Centered',
            parent=styles['Normal'],
            fontName=CJK_FONT,
            fontSize=12,
            leading=20,
            alignment=TA_CENTER,
        )

        grade_style = ParagraphStyle(
            'Grade',
            parent=centered,
            fontName=BOLD_FONT,
            fontSize=18,
            leading=25,
        )

        name_style = ParagraphStyle(
            'Name',
            parent=centered,
            fontName=CJK_FONT,
            fontSize=17,
            leading=24,
            spaceBefore=8,
            spaceAfter=8,
        )

        # -------------------------------------------------------------------
        # Certificate header / student information
        # -------------------------------------------------------------------

        story = [
            Spacer(1, 12),
            Paragraph('AIS3 Junior 2026', title),
            Paragraph(
                f"<font name='{CJK_FONT}'>"
                f"資安實戰能力認證證書"
                f"</font>",
                subtitle,
            ),
            Paragraph(
                f"<font name='{CJK_FONT}'>茲證明 </font>"
                f"<font name='{CJK_FONT}'>{escape(str(student_name))}</font>"
                f"<font name='{CJK_FONT}'> 已完成 AIS3 Junior 2026 實戰能力評核。</font>",
                name_style,
            ),
            Spacer(1, 8),
            Paragraph(
                f"<font name='{CJK_FONT}'>綜合成績：</font>"
                f"{escape(str(student_data['average_score']))}"
                f"<font name='{CJK_FONT}'>　　評級：</font>"
                f"{escape(str(student_data['grade']))}",
                grade_style,
            ),
            Spacer(1, 12),
        ]

        # -------------------------------------------------------------------
        # Score table
        # -------------------------------------------------------------------

        rows = [[
            Paragraph(f"<font name='{CJK_FONT}'>評核項目</font>", centered),
            Paragraph(f"<font name='{CJK_FONT}'>成績</font>", centered),
        ]]

        for key, label in SCORE_LABELS.items():
            rows.append([label, str(student_data['scores'][key])])

        table = Table(rows, colWidths=[300, 100])

        table.setStyle(
            TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), REGULAR_FONT),
                ('FONTNAME', (0, 0), (-1, 0), BOLD_FONT),
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1f2937')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cbd5e1')),
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ])
        )

        story += [
            table,
            Spacer(1, 18),
            Image(chart_path, width=280, height=280),
            Spacer(1, 8),
            Paragraph(
                f"<font name='{CJK_FONT}'>"
                f"本證書由 AIS3 Junior VulnLab 系統核發。"
                f"</font>",
                centered,
            ),
        ]

        doc.build(story)

        _update_certificate(certificate_id, 'issued', file_name)

        return {
            'status': 'success',
            'output': output_path,
            'certificate_id': certificate_id,
        }

    except Exception:
        _update_certificate(certificate_id, 'failed')
        raise

    finally:
        try:
            Path(chart_path).unlink(missing_ok=True)
        except Exception:
            pass