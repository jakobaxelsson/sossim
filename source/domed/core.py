"""
This modules generates basic functionality for creating DOM trees in a Pythonic fashion.
It is inspired by the Python dominate library in its use of context managers to describe the tree structure.
However, it builds the tree directly, instead of creating a temporary structure from which HTML text is generated.
This also makes it possible to add event listeners, modify the DOM dynamically, etc.

A typical usage looks as follows:

```
from domed import document
from domed.html import *

# Get the body element of the document, clearing its current children, and adding new ones.
with document.query(".body").clear():
    with ol():
        with ul():
            with li("Item 1.1"):
                event_listener("click", lambda _: print("Click"))
            li("Item 1.2")
        with li("Item 2") as item:
            item["id"] = "item2"
        li("Item 3", id = "item3")
```
"""
import sys
from typing import Any, Callable, ClassVar, Iterable, Optional, Protocol, Self

Event = Any

class JSDomElement(Protocol):
    """
    Specifies the interface of Javascript DOM elements, for typechecking.
    """
    parentElement: Self | None
    children: list[Self]
    firstChild: Self
    innerHTML: str
    style: Any
    value: Any

    def addEventListener(self, event: str, listener: Callable[[Event], Any]): ...
    def appendChild(self, child: Self): ...
    def cloneNode(self, deep: Optional[bool]) -> Self: ...
    def prepend(self, other: Self): ...
    def querySelector(self, q: str) -> Self: ...
    def querySelectorAll(self, q: str) -> list[Self]: ...
    def remove(self): ...
    def removeChild(self, child: Self): ...
    def getAttribute(self, name: str) -> str: ...
    def setAttribute(self, name: str, value: Any): ...

class JSDocument(Protocol):
    """
    Specifices the interface of the Javascript Document class, for typechecking.
    """
    def createElement(self, tag_name: str) -> JSDomElement: ...
    def createElementNS(self, namespace: str, tag_name: str) -> JSDomElement: ...
    def querySelector(self, q: str) -> Self: ...
    def querySelectorAll(self, q: str) -> Self: ...

if sys.platform == "emscripten":
    import js
    from pyodide.ffi import create_proxy
else:
    # Specifies the interface of the Pyodide entities js and create_proxy, for typechecking.
    class js(Protocol):
        document: JSDocument

    def create_proxy(f: Any) -> Any: ...

class DomElement:
    """
    A class that acts as a context manager for DOM element creation functions.
    """

    # Keep av stack of surrounding contexts.
    stack: ClassVar[list[Self]] = []

    def __init__(self, tag_name: str, content: Optional[str | Self] = None, namespace: Optional[str] = None, **attrs: Any):
        """
        Create the new DOM node with the given tag_name.
        If content is provided as a string, it is assigned to the node as inner HTML.
        If content is provided as a tag, it is added as a child.

        Args:
            tag_name (str): the tag name.
            content (str | Self, optional): content of the DOM node. Defaults to None.
            namespace (str, optional): a name space string. Defaults to None.
            attrs (Any): a dictionary of attribute values. 
        """
        if isinstance(namespace, str):
            self._dom_element = js.document.createElementNS(namespace, tag_name)
        else:
            self._dom_element = js.document.createElement(tag_name)

        # If some content was provided, add it to the node depending on its type.
        if isinstance(content, str):
            # If it is a string, add it as inner HTML
            self._dom_element.innerHTML = content
        elif isinstance(content, DomElement):
            # Otherwise, assume it is a DOM node, and add it as a child
            self._dom_element.appendChild(content._dom_element)

        # If attributes were provided, add them to the node, mapping the names to avoid clashes with Python reserved words.
        for (a, v) in attrs.items():
            self._dom_element.setAttribute(self.map_attribute_name(a), v)

        # If this element is created inside a context, then add it as a child of its parent.
        if DomElement.stack != []:
            DomElement.stack[-1]._dom_element.appendChild(self._dom_element)

    def __enter__(self) -> Self:
        """
        Enter context. Push this element onto the stack, so that it becomes the parent of elements created within the context.

        Returns:
            Self: returns self.
        """
        DomElement.stack.append(self)
        # Return the created DOM element so that it can be bound to the context variable.
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Pops the top element of the stack to return to the outer context.
        """
        DomElement.stack.pop()

    def __getitem__(self, attribute: str) -> str:
        """
        Retrieves an attribute of the DOM element.

        Args:
            attribute (str): the attribute.

        Returns:
            str: returns the attribute value as a string.
        """
        return self._dom_element.getAttribute(attribute)      

    def __setitem__(self, attribute: str, value: Any):
        """
        Changes an attribute of the DOM element.

        Args:
            attribute (str): the attribute.
            value (Any): the new value.
        """
        self._dom_element.setAttribute(attribute, value)      

    def map_attribute_name(self, name: str) -> str:
        """
        Maps a Python compatible alternative attribute name to its HTML attribute name.

        Args:
            name (str): the alternative attribute name.

        Returns:
            str: the HTML attribute name.
        """
        # Workaround to express some HTML attribute names that clash with Python reserved words.
        if name in ["_class", "cls", "className", "class_name"]:
            return "class"
        if name in ["_for", "fr", "htmlFor", "html_for"]:
            return "for"
        if name.startswith("data_"):
            return "data-" + name[5:].replace("_", "-")
        else:
            return name.replace("_", "-")

    @property
    def value(self) -> Any:
        """
        Property getter for the dom element's value attribute.

        Returns:
            Any: the value of the attribute.
        """
        return self._dom_element.value

    @value.setter
    def value(self, val: Any):
        """
        Property getter for the dom element's value attribute.

        Args:
            val (Any): the new value of the attribute.
        """
        self._dom_element.value = val

    @property
    def parent_element(self) -> Self | None:
        """
        Property getter for the dom element's parent element attribute.

        Returns:
            Self | None: the parent DomElement, or None if it has no parent.
        """
        result = self._dom_element.parentElement
        return wrap(result) if result else None

    @property
    def children(self) -> Iterable[Self]:
        """
        Property getter for the dom element's children attribute.

        Returns:
            Iterable[Self]: an iterable over the children DomElements.
        """
        cs = self._dom_element.children
        for i in range(cs.length): # type: ignore
            yield wrap(cs[i])

    def query(self, q) -> Self:
        """
        Returns a tag structure representing the DOM element indicated by the query string.
        A typical usage is: with document.query(...).

        Args:
            q (str): a query string formatted as a CSS selector.

        Raises:
            Exception: the query did not match.

        Returns:
            Self: the first element that matched the query string.
        """
        result = self._dom_element.querySelector(q)
        if result == None:
            raise Exception(f"Query {q} did not give any result")
        return wrap(result)

    def query_all(self, q) -> Iterable[Self]:
        """
        Returns the DOM elements indicated by the query string as an iterable.
        A typical usage is: for elem in document.query_all(...): ...

        Args:
            q (str): a query string formatted as a CSS selector.

        Returns:
            Iterable[Self]: an iterable over all elements that match the query string.
        """
        es = self._dom_element.querySelectorAll(q)
        for i in range(es.length): # type: ignore
            yield wrap(es[i])
        
    def clear(self) -> Self:
        """
        Removes all the children of the element, and returns the element.

        Returns:
            Self: self.
        """
        while (self._dom_element.firstChild):
            self._dom_element.removeChild(self._dom_element.firstChild)
        return self
    
    def remove(self):
        """
        Removes the DOM element from the DOM tree.
        """
        self._dom_element.remove()

    def inner_html(self, text: Any):
        """
        Sets the innerHTML property of the DOM element.

        Args:
            text (Any): the inner_html
        """
        self._dom_element.innerHTML = str(text)

    def visible(self, is_visible: bool = True):
        """
        Changes the visibility of the element.

        Args:
            is_visible (bool, optional): if True, the element becomes visible, and otherwise invisible. Defaults to True.
        """
        self._dom_element.style.display = "block" if is_visible else "none"

    def unwrap(self) -> JSDomElement | JSDocument:
        """
        Returns the javascript DOM element behind a DomElement, for low level access.
        Returns:
            JSDomElement | JSDocument: the javascript DOM element.
        """
        return self._dom_element

class wrap(DomElement):
    """
    Wraps an existing javascript DOM element as a DomElement.
    """
    def __init__(self, js_element: JSDomElement | JSDocument):
        self._dom_element = js_element

# Provide the variable document as a wrapper around js.document
document = wrap(js.document)

def event_listener(event: str, listener: Callable[[Event], Any]):
    """
    Adds an event listener to the current element.

    Args:
        event (str): the event name.
        listener (Callable[[Event], Any]): the listener.
    """
    if DomElement.stack != []:
        DomElement.stack[-1]._dom_element.addEventListener(event, create_proxy(listener))

def create_tag(tag_name: str, namespace: Optional[str] = None) -> Callable[..., DomElement]:
    """
    Returns a function which returns a DOM element with the given name and namespace.
    A typical usage is to create HTML tags. 
    
    Args:
        tag_name (str): the name of the tag.
        namespace (str, optional): the namespace of the tag. Defaults to None.

    Returns:
        Callable[..., DomElement]: a function returning a DOM element wrapper.
    """
    def f(content: Optional[str | DomElement] = None, **attrs: Any):
        return DomElement(tag_name, content, namespace, **attrs)
    return f