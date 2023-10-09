"""
Development server for the SoSSim project.
It is used for local testing of changes to the interactive browser-based simulation.
It implements a simple web server which serves the app files.
It also checks if any of the generated files need updates.
If so, the corresponding build steps are executed before serving those files.
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler

import build

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    Customises the request handler to invoke a build step for certain files and prevent caching.
    """
    def do_GET(self):
        """
        Invoke the build step if any input files have changed for generated files.
        """
        if self.path.endswith("pyconfig.toml"):
            if build.generate_pyconfig_file():
                print("pyconfig file generated")
        if self.path.endswith(".whl"):
            if build.generate_wheel_file():
                print("wheel file generated")
        return super().do_GET()

    def end_headers(self):
        """
        Add headers that prevents browser from caching files.
        """
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

if __name__ == '__main__':
    try:
        server_address = ('', 8000)
        app_url = "http://127.0.0.1:8000/app/sossim.html"
        print(f"Server for interactive simulation started. Go to {app_url} to open simulation.")
        server = HTTPServer(server_address, CustomHTTPRequestHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print('Server stopped.')