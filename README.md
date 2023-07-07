# SoSSim: A Systems-of-Systems Simulator

## Introduction

This library provides a simulator of transportation system.
It is intended to be used for experimenting with different ways of designing systems-of-systems (SoS).
Through the simulation, the effects of different design decisions can be analyzed.

## Usage

The package can be used either in interactive mode or in batch mode.

### Interactive mode

In interactive mode, the simulator runs in the web browser using [pyscript](https://pyscript.net/). 
The browser fetches the necessary files from a web server.

To run the interactive mode locally run `python source/sossim.py -i`.
This starts a local web server from which the files can be fetched to a browser running on the same machine.
Then, open the link [http://127.0.0.1:8000/sossim.html](http://127.0.0.1:8000/sossim.html) in the browser.

The latest commit to the Github respository is automatically published on Github pages.
It can be accessed at [https://jakobaxelsson.github.io/sossim/source/sossim.html](https://jakobaxelsson.github.io/sossim/source/sossim.html).

### Batch mode

In batch mode, the simulator can be run locally from the command line.
First, ensure that all required libraries are installed using `pip install -r requirements.txt`.
Then, run the command `python source/sossim.py`.
This command can take various command line options, which can be enlisted using `python source/sossim.py -h`.

## Implementation

The core of the simulation is an agent-based model developed using the [Mesa](https://mesa.readthedocs.io/) library.
The simulation takes place on a grid map onto which a randomly generated road network is placed.
The road network is implemented as a directed graph using the [NetworkX](https://networkx.org/) library.

The interactive simulation is designed using the [model-view-controller](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller) pattern.
The interface components are created by manipulating the DOM elements of a web page, and the graphics are created in SVG.
The DOM manipulation is done using the `domscript.py` module, which provides a Pythonic approach inspired by the [Dominate](https://github.com/Knio/dominate) library.
However, `domscript.py` works directly on the DOM elements since it executes in the browser, whereas Dominate generates HTML as text and is intended for server side usage.

The Mesa library has some dependencies that are not possible to use in the browser.
Therefore, a copy of the core modules of Mesa have been included in this repository. 

## Development

For development tasks, there is a utility called `build.py` that automates recurring development tasks, such as type checking, generating documentation, etc.
Its features can be checked using `python build.py --help`.

To install the dependencies required for using development utilities, run `pip install -r requirements_development.txt`.

## Documentation

Some [documentation](https://jakobaxelsson.github.io/sossim/documentation/index.html) is available to browse and search.