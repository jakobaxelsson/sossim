This directory contains a minimal version of the Python mesa library.
It only contains the core modules for creating agent based models, and removes support for visualization.
The reason for this is to remove dependency on packages that are not available in pyscript and pyodide.
The files are copied from https://github.com/projectmesa/mesa/tree/main/mesa version 1.2.1.
The package init file is slightly modified to remove references to files not included.

The space module is currently not used, and could be removed.