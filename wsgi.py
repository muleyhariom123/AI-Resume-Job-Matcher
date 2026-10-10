"""
WSGI Application Entry Point
===========================
Used by production WSGI servers such as Waitress (Windows/Cross-platform) 
or Gunicorn (Linux/Container environments).

Startup command on Windows using Waitress:
    waitress-serve --host=127.0.0.1 --port=5000 wsgi:app
or simply:
    python wsgi.py
"""

import os
import logging
from app import create_app

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Instantiate the application using production settings if configured
app = create_app()

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    logging.info(f"Serving AI Resume Matcher via Waitress on {host}:{port}...")
    serve(app, host=host, port=port)
