import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from helper import load_logs

class LogsReqHandler(BaseHTTPRequestHandler):
    # def log_request(self, code = "-", size = "-"):
    #     pass
    
    # def log_message(self, format, *args):
    #     pass

    def do_GET(self):
        # The result address seems to be from Traefik
        if self.path == f'/logs':
            logs = load_logs()
            response = json.dumps(logs, indent=2).encode('utf-8')

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response) # or use byte string for plaintext
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8088), LogsReqHandler)
    print("Listening on port 8088")
    server.serve_forever()