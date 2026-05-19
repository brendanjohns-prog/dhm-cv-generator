"""
DHM CV Optimisation API
-----------------------
Accepts Claude's structured CV JSON via POST /generate or POST /generate-report.
Returns a formatted .docx CV or branded PDF report.
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
        tag_pattern = re.compile(r'\s*[\[\(]\s*(HIGH|MEDIUM|LOW)\s*PRIORITY\s*[\]\)]', re.I)
        item['title'] = tag_pattern.sub('', title).strip()
        item['text'] = tag_pattern.sub('', body).strip()
    return gap_items
CHANGES_FIRST_PAGE = 5
CHANGES_PER_PAGE = 6
GAPS_FIRST_PAGE = 2
GAPS_PER_PAGE = 3
CHANGE_TITLE_MAX = 70
CHANGE_BODY_MAX = 280
GAP_TITLE_MAX = 70
GAP_BODY_MAX = 560
def _trim(text, limit):
    text = (text or '').strip()
    if len(text) <= limit:
        return text
    budget = text[:limit]
    match = re.search(r'^(.*[.!?])(?:\s|$)', budget, re.DOTALL)
    if match:
        return match.group(1).strip()
    return budget.rsplit(' ', 1)[0].rstrip(',;:- ')
def _paginate(items, per_page, first_page=None):
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
    # Cache-bust: a unique comment ensures PDFShift treats every render as
    # new even when the visible content is identical (avoids serving stale PDFs).
    import time as _time
    html = html.replace('</body>', f'<!-- gen {_time.time()} --></body>')
    response = requests.post(
        PDFSHIFT_URL,
        auth=('api', PDFSHIFT_API_KEY),
        headers={'X-Processor-Version': '142'},
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


def parse_text_items(text):
    """Convert a numbered/bulleted free-text string from Claude into [{title, text}, ...]
    for the PDF report generator."""
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


def normalise_report_sections(cv_data):
    """Claude now returns strategic_changelog and gap_report as plain strings.
    Convert them to the [{title, text}, ...] shape that render_report_pdf expects."""
    changelog = cv_data.get('strategic_changelog', cv_data.get('changelog', []))
    if isinstance(changelog, str):
        changelog = parse_text_items(changelog)
    cv_data['changelog'] = changelog or []

    gap = cv_data.get('gap_report', [])
    if isinstance(gap, str):
        gap = parse_text_items(gap)
    cv_data['gap_report'] = gap or []
    return cv_data

def get_cv_data_from_request():
    """Parse, validate, and normalise the incoming request body."""
    raw_body = request.get_data(as_text=True)
    logger.info("RAW REQUEST (first 300 chars): %s", repr(raw_body[:300]))
    cv_data = request.get_json(force=True, silent=True)
    if not cv_data:
        return None, ('No JSON body received', 400)
    if not isinstance(cv_data, dict):
        return None, (f'Expected JSON object, got {type(cv_data).__name__}', 400)

    # Convert string-form strategic_changelog / gap_report to the [{title, text}, ...]
    # shape that render_report_pdf expects.
    cv_data = normalise_report_sections(cv_data)

    # Strip em dashes from all text fields
    cv_data = clean_cv_data(cv_data)
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
