"""
Main file for the SoSSim system-of-systems simulator.
It imports the necessary modules and configures the simulation.
It can be ran in batch mode or in interactive mode in the browser using pyscript.
"""
import sys

from configuration import Configuration

async def import_mesa():
    """
    Installs the mesa library when running the interactive simulation.
    This is a workaround needed since mesa has dependencies that makes it unusable from pyscript or pyodide.
    """
    import micropip # type: ignore
    await micropip.install("mesa", deps = False)
    # It is unclear why the following block is needed, but without it, later imports of mesa sublibraries fail...
    try:
        import mesa # type: ignore
    except:
        pass

async def interactive_mode():
    """
    Runs the simulator in interactive mode in the browser.
    """
    await import_mesa()

    import model
    import user_interface

    configuration = Configuration()

    # Define a global variable ui, which can be used to access all information about the executing system from the Python REPL in the browser.
    global ui

    # Create the model and the user interface.
    mod = model.TransportSystem(configuration)
    ui = user_interface.UserInterface(mod, configuration)

def batch_mode():
    """
    Runs the simulator in batch mode from command line.
    """
    import model

    configuration = Configuration()

    # Parse command line arguments.
    import argparse

    # Add a few extra arguments to the configuration parser.
    configuration.parser.add_argument("-t", "--iterations", type = int, default = 3, help = "number of iterations of the simulation")
    configuration.parser.add_argument("-i", "--interactive", default = False, action = argparse.BooleanOptionalAction, help = "start server for running in interactive mode")
    configuration.parser.add_argument("-p", "--profile", default = False, action = argparse.BooleanOptionalAction, help = "run in batch mode with profiling")

    # Add shorthands for some configuration parameters.
    configuration.parser.add_argument("-N", dest = "TransportSystem.num_vehicles", type = int)
    configuration.parser.add_argument("-r", dest = "TransportSystem.random_seed", type = int)
    configuration.parser.add_argument("-x", dest = "RoadNetworkGrid.width", type = int)
    configuration.parser.add_argument("-y", dest = "RoadNetworkGrid.height", type = int)
    args = configuration.parse_args()

    if args.interactive:
        # Start a web server from which the interactive mode can be accessed
        # TODO: Currently only works if started from top directory.
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        print("Server for interactive simulation started. Go to http://127.0.0.1:8000/source/sossim.html to open simulation.")
        HTTPServer(("", 8000), SimpleHTTPRequestHandler).serve_forever()
    elif args.profile:
        import cProfile, pstats
        with cProfile.Profile() as pr:
            print("Running batch mode simulation with profiling")
            mod = model.TransportSystem(configuration)
            for i in range(args.iterations):
                mod.step()
            stats = pstats.Stats(pr)
            stats.strip_dirs()
            stats.sort_stats("tottime")
            stats.print_stats()
    else:
        # Create the model using the supplied command line arguments, and run it.
        print("Running batch mode simulation")
        mod = model.TransportSystem(configuration)
        for i in range(args.iterations):
            mod.step()

if __name__ == "__main__":
    # Check if the file is running in the browser, in which case interactive mode is chosen, and otherwise run it in batch mode.
    if sys.platform == "emscripten":
        import asyncio
        asyncio.create_task(interactive_mode())
    else:
        batch_mode()