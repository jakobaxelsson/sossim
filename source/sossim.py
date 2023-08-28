"""
Main file for the SoSSim system-of-systems simulator.
It imports the necessary modules and configures the simulation.
It can be ran in batch mode or in interactive mode in the browser using pyscript.
"""
import io
import sys
from traceback import print_exception
import zipfile

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
    try:
        await import_mesa()

        import model
        import user_interface

        configuration = Configuration()

        # Define a global variable ui, which can be used to access all information about the executing system from the Python REPL in the browser.
        global ui

        # Create the model and the user interface.
        mod = model.TransportSystem(configuration)
        ui = user_interface.UserInterface(mod, configuration)
    except Exception as e:
        # Improve error messages when running in browser
        print_exception(e)

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
    configuration.parser.add_argument("-c", "--configuration-file", type = str, default = "", help = "configuration file")
    configuration.parser.add_argument("-o", "--output-file", type = str, default = "", help = "output file")

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
    else:
        # If a configuration file was provided, initiate the configuration from that
        if args.configuration_file:
            if args.configuration_file.endswith(".zip"):
                # Configuration file part of zip archive
                with zipfile.ZipFile(args.configuration_file) as zip_file:
                    with zip_file.open("configuration.json") as conf_file:
                        configuration.from_json(conf_file.read())
            else:
                # Configuration file provided as json
                with open(args.configuration_file, "r") as conf_file:
                    configuration.from_json(conf_file.read())

        # Create the model, and run it with or without profiling
        mod = model.TransportSystem(configuration)
        profiler_output = ""
        if args.profile:
            import cProfile, pstats
            with cProfile.Profile() as pr:
                print("Running batch mode simulation with profiling")
                mod = model.TransportSystem(configuration)
                for i in range(args.iterations):
                    mod.step()
                output_stream = io.StringIO()
                stats = pstats.Stats(pr, stream = output_stream)
                stats.strip_dirs()
                stats.sort_stats("tottime")
                stats.print_stats()
                profiler_output = output_stream.getvalue()
        else:
            print("Running batch mode simulation")
            for i in range(args.iterations):
                mod.step()

        # If an output file was provided, save information to it. Otherwise print the collected ata, if any
        if args.output_file:
            extras = [("profiler_output.txt", profiler_output, "Profiler output")] if profiler_output else []
            archive = mod.to_archive_content(*extras)
            with zipfile.ZipFile(args.output_file, "w") as zip_file:
                for file_name, content in archive.items():
                    zip_file.writestr(file_name, content)
            print("Output saved to", args.output_file)
        elif mod.collect_data:
            for table_name in mod.data_collector.tables.keys():
                if mod.data_collector.has_rows(table_name):
                    print(f"Data for class {table_name}")
                    print(mod.data_collector.get_table_dataframe(table_name), end = "\n\n")

if __name__ == "__main__":
    # Check if the file is running in the browser, in which case interactive mode is chosen, and otherwise run it in batch mode.
    if sys.platform == "emscripten":
        import asyncio
        asyncio.create_task(interactive_mode())
    else:
        batch_mode()