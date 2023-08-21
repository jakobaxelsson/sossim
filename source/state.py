"""
Provides a possibility to declare state variables of classes.
A typical usage would be:

```
    class C:
        x: Annotated[int, "State"]
        ...
```

Then, `get_state_variables(C)` returns a list of all the state variable names declared in this class and its superclasses.
"""
from typing import get_type_hints

def get_state_variables(cls: type) -> list[str]:
    """
    Returns a list of the names of all variables of a class that have been declared as Annotated[T, "State"].

    Args:
        cls (type): the class.

    Returns:
        list[str]: the list of state variables.
    """
    result = []
    for a, t in get_type_hints(cls, include_extras = True).items():
        if t.__metadata__[0] == "State":
            result.append(a)
    return result

def get_all_state_variables(cls: type) -> list[str]:
    """
    Returns all state variables defined in any class that is a subclass of cls.

    Returns:
        list[str]: _description_
    """
    def get_subclasses(cls):
        for subclass in cls.__subclasses__():
            yield from get_subclasses(subclass)
            yield subclass

    result = []
    for s in get_subclasses(cls):
        result += get_state_variables(s)
    return list(set(result))