"""
Main file for the SoSSim system-of-systems simulator.
It imports the necessary modules and configures the simulation.
It can be ran in batch mode or in interactive mode in the browser using pyscript.
"""
import sys

from configuration import Configuration
import model

def interactive_mode(configuration: Configuration) -> None:
    """
    Runs the simulator in interactive mode in the browser.
    """
    import user_interface as ui

    # Create the model and the user interface.
    mod = model.TransportSystem(configuration)
    ui.UserInterface(mod, configuration)

def batch_mode(configuration: Configuration) -> None:
    """
    Runs the simulator in batch mode from command line.
    """
    # Parse command line arguments.
    import argparse
    # Add a few extra arguments to the configuration parser.
    configuration.parser.add_argument("-t", "--iterations", type = int, default = 3, help = "number of iterations of the simulation")
    configuration.parser.add_argument("-i", "--interactive", default = False, action = argparse.BooleanOptionalAction, help = "start server for running in interactive mode")
    args = configuration.parse_args()

    if args.interactive:
        # Start a web server from which the interactive mode can be accessed
        # TODO: Currently only works if started from top directory.
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        print("Server for interactive simulation started. Go to http://127.0.0.1:8000/source/sossim.html to open simulation.")
        HTTPServer(("", 8000), SimpleHTTPRequestHandler).serve_forever()
    else:
        # Create the model using the supplied command line arguments, and run it.
        print("Running batch mode simulation")
        mod = model.TransportSystem(configuration)
        for i in range(args.iterations):
            mod.step()

if __name__ == "__main__":
    # Check if the file is running in the browser, in which case interactive mode is chosen, and otherwise run it in batch mode.
    configuration = Configuration()
    text = configuration.to_json()
    configuration.from_json(text)
    if sys.platform == "emscripten":
        interactive_mode(configuration)
    else:
        batch_mode(configuration)