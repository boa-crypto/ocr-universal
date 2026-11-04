#!/usr/bin/env python3
"""Simple HTTP server with CORS support for development"""

import http.server
import socketserver
import os

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="C:/workSpace/ocr-universal/web", **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def guess_type(self, path):
        mimetype, encoding = super().guess_type(path)
        # Ensure proper MIME types
        if path.endswith('.js'):
            return 'application/javascript', encoding
        if path.endswith('.css'):
            return 'text/css', encoding
        if path.endswith('.html'):
            return 'text/html', encoding
        if path.endswith('.svg'):
            return 'image/svg+xml', encoding
        return mimetype, encoding

if __name__ == '__main__':
    PORT = 9000
    os.chdir("C:/workSpace/ocr-universal/web")
    class ReuseAddrServer(socketserver.TCPServer):
        allow_reuse_address = True
    with ReuseAddrServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()