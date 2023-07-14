"""
Defines configuration handling mechanisms.
"""
import argparse
import json
from typing import Any

class Configuration:
    """
    Configurations are objects that contain all settings for generating a model and running the simulation.
    The intention is that instead of passing individual parameters when creating model objects, the whole configuration is passed.
    The parameters are grouped under different object classes, to which they apply.
    A configuration object can be initialized from command line arguments or a JSON string.
    """

    # Params are stored in a three level dictionary which is defined on the class.
    # The first level is class names, the second is parameter names, and the third is parameter information.
    # The parameter information is type, default, flag (for command line arguments), and help string.
    params = dict()
    # Create a command line parser for the parameters.
    parser = argparse.ArgumentParser(prog = "SoSSIM", 
                                     description = "A system-of-systems simulator for a transport system")

    def __init__(self):
        """
        Creates a configuration object with all parameters set to default values.
        """
        # Values are stored in a three level dictionary defined on the object.
        # The first level is class names, the second is parameter names, and the third is the value.        
        self.data = dict()
        # Initialize all params to their default values
        for c, ps in self.params.items():
            for p, d in ps.items():
                self.set_param_value(c, p, d["default"])

    @classmethod
    def add_param(cls, class_name: str, name: str, type: Any, default: Any, flag: str, help: str) -> None: 
        """
        Adds a parameter to a class, with a type, default value, a command line argument flag, and a help string.
        The current value is set to the default value.
        Typically, this method is called in conjunction with the definition of the class to which it applies.

        Args:
            class_name (str): the name of the class.
            name (str): the name of the parameter.
            type (Any): the type of the parameter.
            default (Any): the default value of the parameter.
            flag (str): a command line argument flag.
            help (str): a help string.
        """
        # Create the subdictionaries
        if class_name not in cls.params:
            cls.params[class_name] = dict()
        p = cls.params[class_name][name] = dict()
        # Add the parameter information
        p["type"] = type
        p["default"] = default
        p["flag"] = flag
        p["help"] = help
        # Update the command line arguments parser.
        cls.parser.add_argument(flag, "--" + name, type = type, default = default, help = help)

    def set_param_value(self, cls: str, name: str, value: Any) -> None:
        """
        Sets the value of a parameter of a certain class.

        Args:
            cls (str): the class to which the parameter belongs.
            name (str): the name of the parameter.
            value (Any): the new value of the parameter.
        """
        if cls not in self.data:
            self.data[cls] = dict()
        self.data[cls].update({ name : value })

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
                for p, v in self.data[c].items():
                    setattr(obj, p, v)

    def parse_args(self) -> Any:
        """
        Updates parameter values from the command line.

        Returns:
            Any: the parsed command line arguments.
        """
        args = self.parser.parse_args()
        # TODO: Updata the data from the parsed arguments.
        for c, ps in self.params.items():
            for p, _ in ps.items():
                self.set_param_value(c, p, getattr(args, p))
        return args

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