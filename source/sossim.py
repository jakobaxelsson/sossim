"""
Main file for the SoSSim system-of-systems simulator.
It imports the necessary modules and configures the simulation.
It can be ran in batch mode or in interactive mode in the browser using pyscript.
"""

import sys

import model

def interactive_mode():
    """
    Runs the simulator in interactive mode in the browser.
    """
    import user_interface as ui

    # Create the model and the user interface.
    mod = model.TransportSystem()
    ui.UserInteface(mod)
    mod.add_view(ui.TransportSystemView(mod))
#    controller = ui.SimulationController(mod)
    mod.generate()

def batch_mode():
    """
    Runs the simulator in batch mode from command line.
    """
    # Parse command line arguments.
    import argparse
    parser = argparse.ArgumentParser(prog = "SoSSIM", description = "A system-of-systems simulator for a transport system")
    parser.add_argument("-N", type = int, default = 3, help = "number of vehicles")
    parser.add_argument("-x", "--width", type = int, default = 20, help = "number of grid cells in x dimension")
    parser.add_argument("-y", "--height", type = int, default = 20, help = "number of grid cells in y dimension")
    parser.add_argument("-r", "--random_seed", type = int, default = None, help = "seed for random number generator")
    parser.add_argument("-t", "--iterations", type = int, default = 3, help = "number of iterations of the simulation")
    parser.add_argument("-i", "--interactive", default = False, action = argparse.BooleanOptionalAction, help = "start server for running in interactive mode")
    args = parser.parse_args()

    if args.interactive:
        # Start a web server from which the interactive mode can be accessed
        # TODO: Currently only works if started from top directory.
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        print("Server for interactive simulation started. Go to http://127.0.0.1:8000/source/sossim.html to open simulation.")
        HTTPServer(("", 8000), SimpleHTTPRequestHandler).serve_forever()
    else:
        # Create the model using the supplied command line arguments, and run it.
        print("Running batch mode simulation")
        mod = model.TransportSystem()
        mod.generate(N = args.N, width = args.width, height = args.height, random_seed = args.random_seed)
        for i in range(args.iterations):
            mod.step()

if __name__ == "__main__":
    # Check if the file is running in the browser, in which case interactive mode is chosen, and otherwise run it in batch mode.
    if sys.platform == "emscripten":
        interactive_mode()
    else:
        batch_mode()