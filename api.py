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
import os
import tempfile
from datetime import datetime

import requests
from flask import Flask, request, send_file, jsonify
from jinja2 import Environment, FileSystemLoader, select_autoescape

from generate_cv import build_cv_only

PDFSHIFT_API_KEY = os.environ.get('PDFSHIFT_API_KEY', '')
PDFSHIFT_URL = 'https://api.pdfshift.io/v3/convert/pdf'
TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html'])
)

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


def annotate_gap_priorities(gap_items):
    """Detect [HIGH/MEDIUM/LOW PRIORITY] tags on each gap item and strip them from the title."""
    for item in gap_items:
        if not isinstance(item, dict):
            continue
        title = item.get('title', '') or ''
        body = item.get('text', '') or ''

        # Search title first, then body, for a priority tag.
        search_blob = title + ' ' + body
        if re.search(r'\bHIGH\b', search_blob, re.I):
            item['priority'] = 'high'
            item['priority_label'] = 'High priority'
        elif re.search(r'\bLOW\b', search_blob, re.I) and 'PRIORITY' in search_blob.upper():
            item['priority'] = 'low'
            item['priority_label'] = 'Low priority'
        else:
            item['priority'] = 'medium'
            item['priority_label'] = 'Medium priority'

        # Strip [PRIORITY] tags wherever they appear.
        tag_pattern = re.compile(r'\s*[\[\(]\s*(HIGH|MEDIUM|LOW)\s*PRIORITY\s*[\]\)]', re.I)
        item['title'] = tag_pattern.sub('', title).strip()
        item['text'] = tag_pattern.sub('', body).strip()
    return gap_items


# Changes page 1 has the section title + lede, so it fits fewer items.
# Continuation pages are header + items + footer, so they hold more.
CHANGES_FIRST_PAGE = 5
CHANGES_PER_PAGE = 6
# Assessment page 1 has the section title + lede + closer line, so it fits 2.
# Continuation pages are header + cards + footer, so they hold 3.
GAPS_FIRST_PAGE = 2
GAPS_PER_PAGE = 3

# Soft character limits for report cards. Claude is told to stay within these,
# but we trim server-side as a safety net so an over-long response never breaks layout.
# Body targets: ~3 lines for changes, ~5 lines for gap cards at current font sizes.
CHANGE_TITLE_MAX = 70
CHANGE_BODY_MAX = 230
GAP_TITLE_MAX = 70
GAP_BODY_MAX = 560


def _trim(text, limit):
    text = (text or '').strip()
    if len(text) <= limit:
        return text
    # Cut at last word boundary before the limit so we don't mid-word truncate.
    cut = text[:limit].rsplit(' ', 1)[0].rstrip(',;:-')
    return cut + '…'


def _paginate(items, per_page, first_page=None):
    """Fixed-size chunk. Optional first_page lets the first page carry a
    different count (e.g. fewer items to make room for a section title)."""
    pages = []
    n = len(items)
    start = 0
    if first_page is not None and n > 0:
        chunk = items[start:first_page]
        for offset, item in enumerate(chunk):
            if isinstance(item, dict):
                item['index'] = offset + 1
        pages.append(chunk)
        start = first_page
    while start < n:
        chunk = items[start:start + per_page]
        for offset, item in enumerate(chunk):
            if isinstance(item, dict):
                item['index'] = start + offset + 1
        pages.append(chunk)
        start += per_page
    return pages


def render_report_pdf(cv_data):
    """Render the HTML report with Jinja2, convert to PDF via PDFShift, return bytes."""
    if not PDFSHIFT_API_KEY:
        raise RuntimeError('PDFSHIFT_API_KEY environment variable is not set')

    template = _jinja_env.get_template('report_template.html')

    changelog = cv_data.get('changelog', []) or []
    gap_report = annotate_gap_priorities(cv_data.get('gap_report', []) or [])

    # Safety-net trim so layout stays clean when Claude exceeds soft limits.
    for item in changelog:
        if isinstance(item, dict):
            item['title'] = _trim(item.get('title', ''), CHANGE_TITLE_MAX)
            item['text'] = _trim(item.get('text', ''), CHANGE_BODY_MAX)
    for item in gap_report:
        if isinstance(item, dict):
            item['title'] = _trim(item.get('title', ''), GAP_TITLE_MAX)
            item['text'] = _trim(item.get('text', ''), GAP_BODY_MAX)

    change_pages = _paginate(changelog, CHANGES_PER_PAGE, first_page=CHANGES_FIRST_PAGE)
    gap_pages = _paginate(gap_report, GAPS_PER_PAGE, first_page=GAPS_FIRST_PAGE)

    # Page numbering: 1 cover, 2 welcome, 3 approach, then changes, gaps, thank-you.
    change_start = 4
    gap_start = change_start + len(change_pages)
    thanks_page = gap_start + len(gap_pages)

    context = {
        'name': cv_data.get('name', 'Client'),
        'tagline': cv_data.get('tagline', ''),
        'date_str': datetime.now().strftime('%B %Y'),
        'change_pages': change_pages,
        'gap_pages': gap_pages,
        'change_start_page': change_start,
        'gap_start_page': gap_start,
        'thanks_page': thanks_page,
    }

    html = template.render(**context)

    response = requests.post(
        PDFSHIFT_URL,
        auth=('api', PDFSHIFT_API_KEY),
        json={
            'source': html,
            'format': 'A4',
            'margin': '0',
            'use_print': True,
            'sandbox': False,
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(f'PDFShift error {response.status_code}: {response.text[:500]}')

    return response.content


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
            part = part.strip().lstrip('0123456789.)- •').strip()
            if not part:
                continue

            # Preferred: Claude returns "**Title** - body" on one line.
            bold_match = re.match(r'\*\*(.+?)\*\*\s*[-–—:]*\s*(.*)', part, re.DOTALL)
            if bold_match:
                title = bold_match.group(1).strip()
                body = bold_match.group(2).strip()
            else:
                # Fallback: title on first line, body on the rest.
                sub = part.split('\n', 1)
                title = sub[0].strip()
                body = sub[1].strip() if len(sub) > 1 else ''

            # Strip any stray markdown bold markers that slipped through.
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
            body = re.sub(r'\*\*(.+?)\*\*', r'\1', body)

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

        pdf_bytes = render_report_pdf(cv_data)
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
