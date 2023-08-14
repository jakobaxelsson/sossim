"""
Defines a generic configuration handling mechanisms.
This allows all configuration parameters to be handled in a single object.
That object can be passed around to all configurable classes, allowing them to extract whatever information they need.
A typical usage is as follows:

```
    from configuration import Configuration, configurable
    from typing import Annotated

    @configurable
    class C:
        param: Annotated[int, "Param", "some help string"] = 3

        def __init__(self, configuration: Configuration):
            configuration.initialize(self)

    configuration = Configuration()
    obj = C(configuration)
    obj.p  # Returns 3
```

Here, the @configurable decorater informs that this is a class that can take configuration parameters.
The type annotated variable param specifies that this is a configuration parameter, with a help string and a default value of 3.
It is given a command line argument --param <value>. 
The help string is shown when printing the help information for the command line.
It can also be used as tooltips in a user interface.
"""
import argparse
import json
from typing import get_type_hints, Any

def configurable(cls: type) -> type:
    """
    A class decorator that processes Param declarations within the class.
    """
    for a, t in get_type_hints(cls, include_extras = True).items():
        if t.__metadata__[0] == "Param":
            Configuration.add_param(class_name = cls.__name__, name = a, default = getattr(cls, a), type = t.__origin__, help = t.__metadata__[1]) # type: ignore
            delattr(cls, a)
    return cls

class Configuration:
    """
    Configurations are objects that contain all settings for generating a model and running the simulation.
    The intention is that instead of passing individual parameters when creating model objects, the whole configuration is passed.
    The parameters are grouped under different object classes, to which they apply.
    A configuration object can be initialized from command line arguments or from a JSON string.
    """

    # Params are stored in a three level dictionary which is defined on the class.
    # The first level is class names, the second is parameter names, and the third is parameter information.
    # The parameter information is type, default, and help string.
    params: dict[str, dict[str, dict[str, Any]]] = dict()

    # Create a command line parser for the parameters.
    parser = argparse.ArgumentParser()

    def __init__(self):
        """
        Creates a configuration object with all parameters set to default values.
        """
        # Values are stored in a three level data dictionary defined on the object.
        # The first level is class names, the second is parameter names, and the third is the value.        
        self.data = dict()

        # Initialize all params in the data to their default values
        for c, ps in self.params.items():
            for p, d in ps.items():
                self.set_param_value(c, p, d["default"])

    @classmethod
    def add_param(cls, class_name: str, name: str, type: Any, default: Any, help: str) -> None: 
        """
        Adds a parameter to a class, with a type, default value, and a help string.
        The current value is set to the default value.
        Typically, this method is called in conjunction with the definition of the class to which it applies.

        Args:
            class_name (str): the name of the class.
            name (str): the name of the parameter.
            type (Any): the type of the parameter.
            default (Any): the default value of the parameter.
            help (str): a help string.
        """
        # Create the subdictionaries
        if class_name not in cls.params:
            cls.params[class_name] = dict()
        p = cls.params[class_name][name] = dict()

        # Add the parameter information
        p["type"] = type
        p["default"] = default
        p["help"] = help

        # Update the command line arguments parser.
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
        output: dict[str, dict[str, Any]] = dict()
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
        # Reset configuration to default values, in case the configuration was saved using a software version with fewer parameters.
        Configuration.__init__(self)
        input = json.loads(text)

        # Convert type names to types using eval.
        for cls, param in input.items():
            for var, value in param.items():
                if var == "type":
                    self.data[cls][var] = eval(value)
                else:
                    self.data[cls][var] = value