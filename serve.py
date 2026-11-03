#!/usr/bin/env python3
"""
Local dev server for Cricket 07 WebGPU recompilation.
Serves files with Cross-Origin-Opener-Policy and Cross-Origin-Embedder-Policy
headers required for SharedArrayBuffer / Emscripten pthreads, plus HTTP Range
support for OPFS streaming.
"""
import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

class COOPCOEPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), COOPCOEPHandler)
    print(f"Serving Cricket 07 at http://localhost:{PORT}/ (with COOP/COEP headers)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
