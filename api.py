"""
DHM CV Optimisation API
-----------------------
Accepts Claude's CV output via POST /generate or POST /generate-report.
Handles both structured JSON and cv_draft text formats.
Returns a formatted .docx file.
"""

import io
import logging
import traceback as tb
import re
from flask import Flask, request, send_file, jsonify
from generate_cv import build_cv_only
from generate_report_html import build_report_html
from xhtml2pdf import pisa
import tempfile
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'DHM CV Generator'})


def strip_em_dashes(text):
    """Replace em dashes (AI-detection signal) with a plain hyphen."""
    if not isinstance(text, str):
        return text
    return re.sub(r'\s*\u2014\s*', ' - ', text)  # — → -


def clean_cv_data(cv_data):
    """Recursively strip em dashes from all string fields."""
    if isinstance(cv_data, dict):
        return {k: clean_cv_data(v) for k, v in cv_data.items()}
    elif isinstance(cv_data, list):
        return [clean_cv_data(i) for i in cv_data]
    elif isinstance(cv_data, str):
        return strip_em_dashes(cv_data)
    return cv_data


def fix_candidate_voice(text):
    """Replace third-person 'the candidate' language with second-person 'you/your'."""
    if not isinstance(text, str):
        return text

    def _repl(replacement):
        def _fn(m):
            matched = m.group(0)
            result = replacement
            if matched[0].isupper():
                result = result[0].upper() + result[1:]
            return result
        return _fn

    text = re.sub(r"the candidate's", _repl("your"), text, flags=re.IGNORECASE)
    text = re.sub(r"the candidate", _repl("you"), text, flags=re.IGNORECASE)
    return text


def apply_voice_fix(cv_data):
    """Apply second-person voice correction to report-only sections."""
    for section in ('changelog', 'gap_report'):
        items = cv_data.get(section, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    item['title'] = fix_candidate_voice(item.get('title', ''))
                    item['text']  = fix_candidate_voice(item.get('text', ''))
    return cv_data


def parse_cv_draft(cv_data):
    """
    Convert {cv_draft, strategic_changelog, gap_report} text format
    into the structured dict that build_cv_only/build_report_only expect.
    """
    raw = cv_data.get('cv_draft', '')
    raw = raw.replace('\\n', '\n')
    lines = [l for l in raw.split('\n')]
    non_empty = [l.strip() for l in lines if l.strip()]

    structured = {
        'name': non_empty[0] if len(non_empty) > 0 else 'NAME UNKNOWN',
        'tagline': non_empty[1] if len(non_empty) > 1 else '',
        'contact': non_empty[2] if len(non_empty) > 2 else '',
        'summary': '',
        'competencies': '',
        'tech_role': False,
        'technical_skills': None,
        'employment': [],
        'earlier_career': [],
        'education': [],
        'notes': '',
        'changelog': [],
        'gap_report': [],
    }

    # Order matters: more specific patterns before broader ones
    SECTION_PATTERNS = {
        'summary':          re.compile(r'EXECUTIVE SUMMARY|PROFESSIONAL SUMMARY|CAREER SUMMARY|SUMMARY', re.I),
        'technical_skills': re.compile(r'TECHNOLOGY STACK|TECHNICAL SKILLS|TECHNOLOGY SKILLS|TOOLS AND TECHNOLOGY|TECH STACK', re.I),
        'competencies':     re.compile(r'CORE COMPETENCIES|KEY COMPETENCIES|COMPETENCIES|KEY SKILLS|SKILLS PROFILE|SKILLS', re.I),
        'employment':       re.compile(r'PROFESSIONAL EXPERIENCE|EMPLOYMENT HISTORY|WORK EXPERIENCE|EMPLOYMENT|EXPERIENCE', re.I),
        'earlier_career':   re.compile(r'EARLIER CAREER|EARLY CAREER|PREVIOUS ROLES|ADDITIONAL EXPERIENCE', re.I),
        'education':        re.compile(r'EDUCATION|QUALIFICATIONS|ACADEMIC|CERTIFICATIONS', re.I),
        'notes':            re.compile(r'NOTES|ADDITIONAL INFORMATION|ADDITIONAL NOTES|REFERENCES', re.I),
    }

    current_section = None
    section_lines = []

    def flush_section():
        if not current_section or not section_lines:
            return
        content = '\n'.join(section_lines).strip()

        if current_section == 'summary':
            structured['summary'] = content
        elif current_section == 'competencies':
            structured['competencies'] = content
        elif current_section == 'technical_skills':
            structured['technical_skills'] = content
        elif current_section == 'notes':
            structured['notes'] = content
        elif current_section == 'education':
            for line in section_lines:
                line = line.strip()
                if line:
                    structured['education'].append(line)
        elif current_section in ('employment', 'earlier_career'):
            roles = []
            current_role = None
            for line in section_lines:
                line = line.strip()
                if not line:
                    continue
                is_bullet = line.startswith('•') or line.startswith('-') or line.startswith('*')
                is_header = bool(re.search(r'\d{4}', line)) and '|' in line
                if is_header:
                    if current_role:
                        roles.append(current_role)
                    current_role = {'header': line, 'context': '', 'bullets': []}
                elif current_role is not None:
                    if is_bullet:
                        bullet_text = line.lstrip('•-* ').strip()
                        if bullet_text:
                            current_role['bullets'].append(bullet_text)
                    elif not current_role['context']:
                        current_role['context'] = line
                    else:
                        current_role['context'] += ' ' + line
                else:
                    roles.append({'title': line, 'text': ''})
            if current_role:
                roles.append(current_role)

            if current_section == 'employment':
                structured['employment'] = roles
            else:
                ec_items = []
                for r in roles:
                    title = r.get('header', r.get('title', ''))
                    title = title.lstrip('-•* ').strip()
                    context = r.get('context', r.get('text', ''))
                    bullets = r.get('bullets', [])
                    combined = title
                    if context:
                        combined += ' - ' + context
                    if bullets:
                        combined += (' - ' if not context else '; ') + '; '.join(bullets)
                    if combined:
                        ec_items.append(combined)
                structured['earlier_career'] = ec_items

    for line in lines[3:]:
        stripped = line.strip()
        matched = None
        for sec, pattern in SECTION_PATTERNS.items():
            if pattern.fullmatch(stripped) or (stripped.isupper() and len(stripped) > 3 and pattern.search(stripped)):
                matched = sec
                break
        if matched:
            flush_section()
            current_section = matched
            section_lines = []
        elif current_section:
            section_lines.append(line)

    flush_section()

    def parse_text_items(text):
        if not text:
            return []
        text = text.replace('\\n', '\n')
        items = []
        parts = re.split(r'\n(?=\d+[\.\)]\s|\-\s|\•\s)', text)
        for part in parts:
            part = part.strip().lstrip('0123456789.)- •')
            if not part:
                continue
            sub = part.split('\n', 1)
            title = sub[0].strip()
            body = sub[1].strip() if len(sub) > 1 else ''
            items.append({'title': title, 'text': body})
        if not items and text.strip():
            items.append({'title': 'Notes', 'text': text.strip()})
        return items

    structured['changelog'] = parse_text_items(cv_data.get('strategic_changelog', ''))
    structured['gap_report'] = parse_text_items(cv_data.get('gap_report', ''))

    return structured


def get_cv_data_from_request():
    """Parse, validate, and normalise the incoming request body."""
    raw_body = request.get_data(as_text=True)
    logger.info("RAW REQUEST (first 300 chars): %s", repr(raw_body[:300]))

    cv_data = request.get_json(force=True, silent=True)
    if not cv_data:
        return None, ('No JSON body received', 400)
    if not isinstance(cv_data, dict):
        return None, (f'Expected JSON object, got {type(cv_data).__name__}', 400)

    if 'cv_draft' in cv_data:
        logger.info("Detected cv_draft format — converting to structured")
        cv_data = parse_cv_draft(cv_data)

    # Strip em dashes from all text fields
    cv_data = clean_cv_data(cv_data)
    # Fix AI-generated third-person voice in report sections
    cv_data = apply_voice_fix(cv_data)
    return cv_data, None


@app.route('/generate', methods=['POST'])
def generate():
    """Returns the client-facing CV document only (no changelog/gap report)."""
    try:
        cv_data, err = get_cv_data_from_request()
        if err:
            return jsonify({'error': err[0]}), err[1]

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            output_path = tmp.name

        build_cv_only(cv_data, output_path)
        logger.info("CV saved: %s", output_path)

        return send_file(
            output_path,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name='DHM_CV_Output.docx'
        )
    except Exception as e:
        logger.error("Exception: %s\n%s", e, tb.format_exc())
        return jsonify({'error': str(e), 'traceback': tb.format_exc()}), 400


@app.route('/generate-report', methods=['POST'])
def generate_report():
    """Returns the branded PDF report (cover + welcome + approach + changelog + gap report)."""
    try:
        cv_data, err = get_cv_data_from_request()
        if err:
            return jsonify({'error': err[0]}), err[1]

        html_content = build_report_html(cv_data)
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        if pisa_status.err:
            raise Exception(f'PDF generation failed with {pisa_status.err} errors')
        pdf_bytes = pdf_buffer.getvalue()
        logger.info("Report PDF generated (%d bytes)", len(pdf_bytes))

        candidate_name = cv_data.get('name', 'Client').replace(' ', '_')
        filename = f'DHM_CV_Report_{candidate_name}.pdf'

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error("Exception: %s\n%s", e, tb.format_exc())
        return jsonify({'error': str(e), 'traceback': tb.format_exc()}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
