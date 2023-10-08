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
    Customises the request handler to invoke a build step for certain files.
    """
    def do_GET(self) -> None:
        if self.path.endswith("pyconfig.toml"):
            if build.generate_pyconfig_file():
                print("pyconfig file generated")
        if self.path.endswith(".whl"):
            if build.generate_wheel_file():
                print("wheel file generated")
        return super().do_GET()

# Start a web server from which the interactive mode can be accessed
print("Server for interactive simulation started. Go to http://127.0.0.1:8000/app/sossim.html to open simulation.")
HTTPServer(("", 8000), CustomHTTPRequestHandler).serve_forever()