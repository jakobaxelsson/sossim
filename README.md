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

To run the interactive mode locally run `python -m sossim -i`.
This starts a local web server from which the files can be fetched to a browser running on the same machine.
Then, open the link [http://127.0.0.1:8000/sossim/sossim.html](http://127.0.0.1:8000/sossim/sossim.html) in the browser.

### Using Docker
A Dockerfile is provided for running the software without installing Python or any libraries.
To use, first build a Docker container using `docker build -t sossim .`.
Then, run the interactive mode using `docker run --name sossim -d -p 8000:8000 sossim`.
To stop the container, use `docker kill sossim` followed by `docker rm sossim` to remove the container.

### Batch mode

In batch mode, the simulator can be run locally from the command line.
First, ensure that all required libraries are installed using `pip install -r requirements.txt`.
Then, run the command `python -m sossim`.
This command can take various command line options, which can be enlisted using `python -m sossim -h`.

### Live demonstration

The latest commit to the Github respository is automatically published on Github pages.
It can be accessed as a [live demonstration](https://jakobaxelsson.github.io/sossim/sossim/sossim.html).
This does not require any local installations whatsoever.

## Implementation

In this section, some more details are provided on how the software is implemented.

### Dependencies

The core of the simulation is an agent-based model developed using the [Mesa](https://mesa.readthedocs.io/) library.
The Mesa library has some dependencies that are not possible to use in the browser.
Therefore, a copy of the core modules of Mesa has been included in this repository. 

The simulation takes place on a grid map onto which a randomly generated road network is placed.
The road network is implemented as a directed graph using the [NetworkX](https://networkx.org/) library.

### User interface

The interactive simulation is designed using the [model-view-controller](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller) pattern.
The interface components are created by manipulating the DOM elements of a web page, and the graphics are created in SVG.
The DOM manipulation is done using the `domed` package, which provides a Pythonic approach inspired by the [Dominate](https://github.com/Knio/dominate) library.
However, `domed` works directly on the DOM elements since it executes in the browser, whereas Dominate generates HTML as text and is intended for server side usage.

For development purposes, there is also a Python REPL accessible in the user interface, through the View menu.
Through this, it is possible to access the user interface object using the variable `ui`.
This in turn gives access to all parts of the system.
As an example, to get the list of all agents, evaluate the expression `ui.model.agents()`.

### Configurations

The models and simulation have a large number of different configuration parameters.
This are accessible both as command line arguments when running in batch mode, and as an interactive dialogue in the user interface.
The configurations can also be saved and restored, in order to recreate a certain simulation.
To handle the configurations in a smooth way, a Configuration class is provided which gathers all parameters.
In that way, a single configuration object can be passed around to various functions, rather than individual specific parameters.
Special syntax is provided to make the specification of parameters relevant to a certain class as readable as possible.

## Development

For development tasks, there is a utility called `build.py` that automates recurring development tasks, such as type checking, generating documentation, etc.
Its features can be checked using `python build.py --help`.

To install the dependencies required for using development utilities, run `pip install -r requirements_development.txt`.

## Documentation

Some [documentation](https://jakobaxelsson.github.io/sossim/documentation/index.html) is available to browse and search.
Those modules that contain non-trivial class structures also come with partial UML class diagrams.
These illustrate some of the key relations and attributes of the classes.