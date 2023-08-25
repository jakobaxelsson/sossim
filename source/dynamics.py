"""
Provides support for describing dynamics of entities.
This includes a possibility to declare state variables of classes.
A typical usage would be:

```
    class C:
        x: Annotated[int, "State"]
        ...
```

Then, `state_variables(C)` returns a list of all the state variable names declared in this class and its superclasses.
"""
from typing import get_type_hints


def state_variables(cls: type) -> list[str]:
    """
    Returns a list of the names of all variables of a class that have been declared as Annotated[T, "State"].

    Args:
        cls (type): the class.

    Returns:
        list[str]: the list of state variables.
    """
    result = []
    for a, t in get_type_hints(cls, include_extras=True).items():
        if t.__metadata__[0] == "State":
            result.append(a)
    return result


def all_state_variables(cls: type) -> dict[str, list[str]]:
    """
    Returns all state variables defined in any class that is a subclass of cls.
    The result is a dict, that maps each class name to a list of state variables.

    Returns:
        dict[str, list[str]]: the state variables for each class.
    """

    def all_subclasses(cls):
        # An iterator that recursively traverses all subclasses of a class
        for subclass in cls.__subclasses__():
            yield from all_subclasses(subclass)
            yield subclass

    return { s.__name__ : state_variables(s) for s in all_subclasses(cls)}