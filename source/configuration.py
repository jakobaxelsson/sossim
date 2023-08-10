"""
Defines configuration handling mechanisms.
"""
import argparse
import inspect
import json
from typing import get_type_hints, Any, Generic, Type, TypeVar

T = TypeVar("T")

class Param(Generic[T]):
    """
    Param is a class holding the information provided when declaring a configuration parameter using type hints.
    It is typically used as follows:

    @configurable
    class C:
        param: Param(int, flag = "-p") = 3   # some help string

    The comment at the end of line is recuperated, and used as a help string for the parameter (unless another help string is provided).
    """
    def __init__(self, type: Type[T], flag: str = "", help: str = ""):
        self.type = type
        self.flag = flag
        if help:
            self.help = help
        else:
            # Fetch the help message from a comment at the end of the line where the Param was created.
            # Get the caller's frame
            frame = inspect.currentframe().f_back
            # Get the file line number where the call to Param occured
            code_line = frame.f_lineno # This is the line in the file
            # Get the source code of the class and the line in the file where the class definition starts
            source_code, start_line = inspect.getsourcelines(frame)
            # Get the relevant source line
            source_line = source_code[code_line - start_line]
            # Extract the comment at the end of the line
            try:
                comment = source_line.split("#")[1].strip()
            except Exception:
                comment = ""
            if comment:
                self.help = comment

def configurable(cls: type) -> type:
    """
    A class decorator that indicates that processes Param declarations within the class.
    """
    for a, t in get_type_hints(cls).items():
        if isinstance(t, Param):
            Configuration.add_param(class_name = cls.__name__, name = a, default = getattr(cls, a), type = t.type, flag = t.flag, help = t.help) # type: ignore
            delattr(cls, a)
    return cls

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
        if flag:
            cls.parser.add_argument(flag, "--" + name, type = type, default = default, help = help)
        else:
            cls.parser.add_argument("--" + name, type = type, default = default, help = help)

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
        output = dict()
        # Convert type objects to str, to be able to serialize.
        for cls, param in self.data.items():
            output[cls] = dict()
            for var, value in param.items():
                if var == "type":
                    output[cls][var] = value.__name__
                else:
                    output[cls][var] = value
        return json.dumps(output, indent = 4)
    
    def from_json(self, text: str):
        """
        Updates the configuration with the values provided in the JSON formatted text.

        Args:
            text (str): a JSON representation of a configuration.
        """
        # Reset configuration to default values, in case some parameters have been added to code after configuration was saved.
        self.__init__()
        input = json.loads(text)
        # Convert type names to types using eval.
        for cls, param in input.items():
            for var, value in param.items():
                if var == "type":
                    self.data[cls][var] = eval(value)
                else:
                    self.data[cls][var] = value