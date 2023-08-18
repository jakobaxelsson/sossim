"""
The `domed` package contains functionality for directly manipulating the DOM structure in a pythonic way.
It is intended for use with Pyodide or Pyscript, for running Python in the browser.
The top module of the package contains generic functions and classes.
The submodules `html` and `svg` define all the tags available for writing HTML and SVG. 
"""
import sys
if sys.platform != "emscripten":
    raise ImportError("The domed package can only be used for code running in a browser")