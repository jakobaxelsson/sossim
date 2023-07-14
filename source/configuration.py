"""
Defines configuration handling mechanisms.
"""
import argparse
import json
import random
import sys
from typing import Any

class Configuration:
    """
    Configurations are objects that contain all settings for generating a model and running the simulation.
    The intention is that instead of passing individual parameters when creating model objects, the whole configuration is passed.
    The parameters are grouped under different object classes, to which they apply.
    A configuration object can be initialized from command line arguments or a JSON string.
    """
    def __init__(self):
        """
        Creates a configuration object with all parameters set to default values.
        """
        # Data is stored in a three level dictionary.
        # The first level is class names, the second is parameter names, and the third is parameter information.
        # The parameter information is type, default, value, flag (for command line arguments), and help string.
        self.data = dict()
        # Create a command line parser for the parameters.
        self.parser = argparse.ArgumentParser(prog = "SoSSIM", 
                                              description = "A system-of-systems simulator for a transport system")
        # Add parameters
        self.add_params()

    def add_params(self):
        """
        Adds all the parameters for the configuration.
        """
        self.add_param(cls = "TransportSystem", name = "num_agents", type = int, default = 10, flag = "-N", 
                       help = "number of vehicles")
        self.add_param(cls = "TransportSystem", name = "width", type = int, default = 10, flag = "-x", 
                       help = "number of grid cells in x dimension")
        self.add_param(cls = "TransportSystem", name = "height", type = int, default = 10, flag = "-y", 
                       help = "number of grid cells in y dimension")
        self.add_param(cls = "TransportSystem", name = "destination_density", type = float, default = 0.3, flag = "-dd", 
                       help = "probability of generating a destination in a position where it is possible")
        self.add_param(cls = "TransportSystem", name = "random_seed", type = int, default = random.randrange(sys.maxsize), flag = "-r", 
                       help = "seed for random number generator")
    
    def add_param(self, cls: str, name: str, type: Any, default: Any, flag: str, help: str) -> None: 
        """
        Adds a parameter to a class, with a type, default value, a command line argument flag, and a help string.
        The current value is set to the default value.

        Args:
            cls (str): the name of the class.
            name (str): the name of the parameter.
            type (Any): the type of the parameter.
            default (Any): the default value of the parameter.
            flag (str): a command line argument flag.
            help (str): a help string.
        """
        # Create the subdictionaries
        if cls not in self.data:
            self.data[cls] = dict()
        d = self.data[cls][name] = dict()
        # Add the parameter information
        d["type"] = type
        d["default"] = d["value"] = default
        d["flag"] = flag
        d["help"] = help
        # Update the command line arguments parser.
        self.parser.add_argument(flag, "--" + name, type = type, default = default, help = help)

    def set_param_value(self, cls: str, name: str, value: Any) -> None:
        """
        Sets the value of a parameter of a certain class.

        Args:
            cls (str): the class to which the parameter belongs.
            name (str): the name of the parameter.
            value (Any): the new value of the parameter.
        """
        self.data[cls][name]["value"] = value

    def initialize(self, obj: Any):
        """
        Initializes object attributes according to the configuration.

        Args:
            obj (Any): the object to be initialized.
        """
        # Get the names of all the object's superclasses
        superclasses = [c.__name__ for c in obj.__class__.__mro__]
        # Iterate over all the params of all the superclasses
        for c in superclasses:
            if c in self.data:
                for p, d in self.data[c].items():
                    setattr(obj, p, d["value"])

    def parse_args(self) -> None:
        """
        Updates parameter values from the command line.
        """
        self.parser.parse_args()
        # TODO: Updata the data from the parsed arguments.

    def to_json(self) -> str:
        """
        Generates a string containing the JSON representation of the configuration.

        Returns:
            str: a JSON representation of the configuration.
        """
        # TODO: This doesn't work. The "type" field does not serialize.
        return json.dumps(self.data, indent = 4)
    
    def from_json(self, text: str):
        """
        Updates the configuration with the values provided in the JSON formatted text.

        Args:
            text (str): a JSON representation of a configuration.
        """
        # TODO: This doesn't work. The "type" field does not serialize.
        self.data = json.loads(text)