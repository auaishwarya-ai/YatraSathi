"""
YatraSathi - run this file to start the web application.

    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""
import os

from yatrasathi import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    print(f"\n  YatraSathi is running at  http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)
