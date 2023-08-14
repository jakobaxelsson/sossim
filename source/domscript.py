"""
This modules generates basic functionality for creating DOM trees in a Pythonic fashion.
It is inspired by the Python dominate library in its use of context managers to describe the tree structure.
However, it builds the tree directly, instead of creating a temporary structure from which HTML text is generated.
This also makes it possible to add event listeners, modify the DOM dynamically, etc.

A typical usage looks as follows:

```
from domscript import *

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

"""
TODO:
- Add show/hide methods to the tag class. They can be used as e.g. document.query("...").show().
  It should set the property "display" to "initial" or "none. self.dom_element.style.setProperty("display", "initial")
"""
import sys
from typing import Any, Callable, ClassVar, Optional, Protocol, Self

Event = Any

class JSDomElement(Protocol):
    """
    Specifies the interface of Javascript DOM elements, for typechecking.
    """
    firstChild: Self = ...
    innerHTML: str = ...

    def addEventListener(self, event: str, listener: Callable[[Event], Any]): ...
    def appendChild(self, child: Self): ...
    def querySelector(self, q: str) -> Self: ...
    def remove(self): ...
    def removeChild(self, child: Self): ...
    def setAttribute(self, name: str, value: Any): ...

class JSDocument(Protocol):
    """
    Specifices the interface of the Javascript Document class, for typechecking.
    """
    def createElement(self, tag_name: str) -> JSDomElement: ...
    def createElementNS(self, namespace: str, tag_name: str) -> JSDomElement: ...
    def querySelector(self, q: str) -> Self: ...

if sys.platform == "emscripten":
    import js
    from pyodide.ffi import create_proxy
else:
    # Specifies the interface of the Pyodide entities js and create_proxy, for typechecking.
    class js(Protocol):
        document: JSDocument = ...

    def create_proxy(f: Any) -> Any: ...

class DomWrapper:
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
            self.dom_element = js.document.createElementNS(namespace, tag_name)
        else:
            self.dom_element = js.document.createElement(tag_name)

        # If some content was provided, add it to the node depending on its type.
        if isinstance(content, str):
            # If it is a string, add it as inner HTML
            self.dom_element.innerHTML = content
        elif isinstance(content, DomWrapper):
            # Otherwise, assume it is a DOM node, and add it as a child
            self.dom_element.appendChild(content.dom_element)

        # If attributes were provided, add them to the node, mapping the names to avoid clashes with Python reserved words.
        for (a, v) in attrs.items():
            self.dom_element.setAttribute(self.map_attribute_name(a), v)

        # If this element is created inside a context, then add it as a child of its parent.
        if DomWrapper.stack != []:
            DomWrapper.stack[-1].dom_element.appendChild(self.dom_element)

    def __enter__(self) -> Self:
        """
        Enter context. Push this element onto the stack, so that it becomes the parent of elements created within the context.

        Returns:
            Self: returns self.
        """
        DomWrapper.stack.append(self)
        # Return the created DOM element so that it can be bound to the context variable.
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Pops the top element of the stack to return to the outer context.
        """
        DomWrapper.stack.pop()

    def __setitem__(self, attribute: str, value: Any):
        """
        Changes an attribute of the DOM element.

        Args:
            key (str): the attribute.
            value (Any): the new value.
        """
        self.dom_element.setAttribute(attribute, value)      

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

    def query(self, q) -> "DomWrapper":
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
        result = self.dom_element.querySelector(q)
        if result == None:
            raise Exception(f"Query {q} did not give any result")
        return dom(result)
        
    def clear(self) -> Self:
        """
        Removes all the children of the element, and returns the element.

        Returns:
            Self: self.
        """
        while (self.dom_element.firstChild):
            self.dom_element.removeChild(self.dom_element.firstChild)
        return self
    
    def remove(self):
        """
        Removes the DOM element from the DOM tree.
        """
        self.dom_element.remove()

    def inner_html(self, text: Any):
        """
        Sets the innerHTML property of the DOM element.

        Args:
            text (Any): the inner_html
        """
        self.dom_element.innerHTML = str(text)

class dom(DomWrapper):
    """
    A context manager for specifying an existing DOM node, that can be used as a parent of a new dom tree.
    """
    def __init__(self, parent_node = js.document):
        self.dom_element = parent_node

# Provide the variable document as a wrapper around js.document
document = dom()

def event_listener(event: str, listener: Callable[[Event], Any]):
    """
    Adds an event listener to the current element.

    Args:
        event (str): the event name.
        listener (Callable[[Event], Any]): the listener.
    """
    if DomWrapper.stack != []:
        DomWrapper.stack[-1].dom_element.addEventListener(event, create_proxy(listener))

def create_tag(tag_name: str, namespace: Optional[str] = None) -> Callable[..., DomWrapper]:
    """
    Returns a function which returns a DOM element with the given name and namespace.
    A typical usage is to create HTML tags. 
    
    Args:
        tag_name (str): the name of the tag.
        namespace (str, optional): the namespace of the tag. Defaults to None.

    Returns:
        Callable[..., DomWrapper]: a function returning a DOM element wrapper.
    """
    def f(content: Optional[str | DomWrapper] = None, **attrs: Any):
        return DomWrapper(tag_name, content, namespace, **attrs)
    return f

# Concrete HTML and SVG tag names
html_tags = "a abbr acronym address applet area article aside audio b base basefont bdi bdo big blockquote body " \
    "br button canvas caption center cite code col colgroup data datalist dd del details dfn dialog dir div dl " \
    "dt em embed fieldset figcaption figure font footer form frame frameset h1 h2 h3 h4 h5 h6 head header hr " \
    "html i iframe img ins kbd label legend li link main map mark meta meter nav noframes noscript object " \
    "ol optgroup option output p param picture pre progress q rp rt ruby s samp script section select small " \
    "source span strike strong style sub summary sup svg table tbody td template textarea tfoot th thead time " \
    "title tr track tt u ul var video wbr"

svg_tags = "altGlyph altGlyphDef altGlyphItem animate animateColor animateMotion animateTransform circle " \
    "clipPath color-profile cursor defs desc ellipse feBlend feColorMatrix feComponentTransfer feComposite " \
    "feConvolveMatrix feDiffuseLighting feDisplacementMap feDistantLight feFlood feFuncA feFuncB feFuncG " \
    "feFuncR feGaussianBlur feImage feMerge feMergeNode feMorphology feOffset fePointLight feSpecularLighting " \
    "feSpotLight feTile feTurbulence filter font font-face font-face-format font-face-name font-face-src " \
    "font-face-uri foreignObject g glyph glyphRef hkern image line linearGradient marker mask metadata " \
    "missing-glyph mpath path pattern polygon polyline radialGradient rect solidColor stop style svg " \
    "switch symbol text textPath title tref tspan use view vkern"

# Create the HTML tag and bind them in the global namespace.
for t in html_tags.split(" "):
    globals()[t] = create_tag(t)

# Create the SVG tag and bind them in the global namespace.
for t in svg_tags.split(" "):
    globals()[t] = create_tag(t, "http://www.w3.org/2000/svg")

# Special treatment for some tags whose name collide with Python symbols
input_ = create_tag("input")
set_ = create_tag("set")