"""
DHM CV Optimisation API
-----------------------
Accepts Claude's structured JSON output via POST /generate
Returns a formatted .docx file ready for Google Drive upload.

Deploy to Render.com -- see README in outputs folder for instructions.
"""

import logging
import traceback as tb
from flask import Flask, request, send_file, jsonify
from generate_cv import build_cv_doc
import tempfile
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check -- Make.com can ping this to confirm the API is live."""
    return jsonify({'status': 'ok', 'service': 'DHM CV Generator'})


@app.route('/generate', methods=['POST'])
def generate():
    """
    Accepts Claude's structured CV JSON via POST body.
    Returns a formatted .docx file as a binary download.
    """
    try:
        raw_body = request.get_data(as_text=True)
        logger.info("=== RAW REQUEST BODY (first 500 chars) ===")
        logger.info(repr(raw_body[:500]))
        logger.info("=== CONTENT-TYPE: %s ===", request.content_type)

        cv_data = request.get_json(force=True, silent=True)

        if not cv_data:
            logger.error("JSON PARSE FAILED. Raw body repr: %s", repr(raw_body[:300]))
            return jsonify({'error': 'No JSON body received', 'raw_preview': raw_body[:200]}), 400

        if not isinstance(cv_data, dict):
            logger.error("cv_data is not a dict, type=%s, value=%s", type(cv_data).__name__, repr(str(cv_data)[:300]))
            return jsonify({'error': f'Expected JSON object, got {type(cv_data).__name__}', 'preview': str(cv_data)[:200]}), 400

        logger.info("cv_data keys: %s", list(cv_data.keys()))

        # Validate minimum required fields
        required = ['name', 'summary', 'employment']
        missing = [f for f in required if f not in cv_data]
        if missing:
            return jsonify({'error': f'Missing required fields: {missing}'}), 400

        # Generate .docx to a temp file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp_path = tmp.name

        build_cv_doc(cv_data, tmp_path)

        # Build a clean filename from candidate name
        raw_name = cv_data.get('name', 'CV_Output')
        safe_name = raw_name.replace(' ', '_').replace('/', '-')
        filename = f"DHM_CV_{safe_name}.docx"

        response = send_file(
            tmp_path,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )

        # Clean up temp file after response is sent
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return response

    except KeyError as e:
        logger.error("KeyError: %s\n%s", e, tb.format_exc())
        return jsonify({'error': f'Missing field in CV data: {str(e)}', 'detail': tb.format_exc()}), 400
    except Exception as e:
        logger.error("Exception: %s\n%s", e, tb.format_exc())
        return jsonify({'error': str(e), 'detail': tb.format_exc()}), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
