"""
This modules generates basic functionality for creating DOM trees in a Pythonic fashion.
It is inspired by the Python dominate library in its use of context managers to describe the tree structure.
However, it builds the tree directly, instead of creating a temporary structure from which HTML text is generated.
This also makes it possible to add event listeners, modify the DOM dynamically, etc.

A typical usage looks as follows:

from domscript import *

with dom().query(".body"):
    with ol():
        with ul():
            with li("Item 1.1"):
                add_event_listener("click", lambda _: js.console.log("Click"))
            li("Item 1.2")
        with li("Item 2") as item:
            item["id"] = "item2"
        li("Item 3", id = "item3")
"""

"""
TODO:
- A recurring pattern is to check if a parent exists, and if it doesn't, create it in some place. Maybe this can be handled as follows:
  If an id is provided, and there is already an element with the same id, then it is reused (but cleared), and otherwise it is created anew.
- Maybe enforce so that a block element cannot be a child of an inline element.
- Make another module for picocss that defines its tags.
- Add show/hide methods to the tag class. They can be used as e.g. dom().query("...").show().
  It should set the property "display" to "initial" or "none. self.dom_element.style.setProperty("display", "initial")
"""

import js
from pyodide.ffi import create_proxy

class tag:
    """
    A class that acts as a context manager for DOM element creation functions.
    """

    # Keep av stack of surrounding contexts.
    stack = []

    def __init__(self, tag_name, content = None, namespace = None, **attrs):
        # Create the new DOM node
        if namespace == None:
            self.dom_element = js.document.createElement(tag_name)
        else:
            self.dom_element = js.document.createElementNS(namespace, tag_name)

        # If some content was provided, add it to the node depending on its type.
        if isinstance(content, str):
            # If it is a string, add it as inner HTML
            self.dom_element.innerHTML = content
        elif content != None:
            # Otherwise, assume it is a DOM node, and add it as a child
            self.dom_element.appendChild(content.dom_element)

        # If attributes were provided, add them to the node, mapping the names to avoid clashes with Python reserved words.
        for (a, v) in attrs.items():
            self.dom_element.setAttribute(self.map_attribute_name(a), v)
        self.attach_element()

    def attach_element(self):
        # Attaches the dom element in the appropriate place in the DOM structure.
        if tag.stack != []:
            # This element is created inside a context. Add context information and then add it as a child of its parent.
            elem = tag.stack[-1].contextualize(self)
            tag.stack[-1].dom_element.appendChild(elem.dom_element)

    def contextualize(self, child):
        # Adds context information, such as styling, classes, attributes, to a child.
        # It can be redefined in subclasses when adapting to CSS frameworks.
        return child

    def __enter__(self):
        # Push this element onto the stack, so that it becomes the parent of elements created within the context.
        tag.stack.append(self)
        # Return the created DOM element so that it can be bound to the context variable.
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Pop the top element of the stack to return to the outer context.
        tag.stack.pop()

    def __setitem__(self, key, value):
        # Changes an attribute of the DOM element in whose context this method is called.
        if tag.stack != []:
            tag.stack[-1].dom_element.setAttribute(key, value)

    def map_attribute_name(self, name):
        # Workaround to express some HTML attribute names that clash with Python reserved words.
        if name in ["_class", "cls", "className", "class_name"]:
            return "class"
        if name in ["_for", "fr", "htmlFor", "html_for"]:
            return "for"
        if name.startswith("data_"):
            return "data-" + name[5:].replace("_", "-")
        else:
            return name.replace("_", "-")

    def query(self, q, clear = False):
        # Returns a tag structure representing the DOM element indicated by the query string.
        # A typical usage is: with dom().query(...).
        result = self.dom_element.querySelector(q)
        if result == None:
            raise Exception(f"Query {q} did not give any result")
        # If clear is True, remove all existing children.
        if clear:
            while (result.firstChild):
                result.removeChild(result.firstChild)
        return dom(result)
    
    def remove(self):
        # Removes the DOM element from the DOM tree.
        self.dom_element.remove()
        self.dom_element = None

    def inner_html(self, text):
        # Sets the innerHTML property of the DOM element.
        self.dom_element.innerHTML = str(text)

class dom(tag):
    """
    A context manager for specifying an existing DOM node, that can be used as a parent of a new dom tree.
    """
    def __init__(self, parent_node = js.document.body):
        self.dom_element = parent_node
 
def add_text(content):
    # Creates a text node, and attaches it in the DOM tree.
    # TODO: Is this really necessary? It can be handled using the tags p (for block) and span (for inline).
    if tag.stack != []:
        # This element is created inside a context. Add it as a child of its parent.
        tag.stack[-1].dom_element.appendChild(js.document.createTextNode(content))

def add_event_listener(event, listener):
    # Adds an event listener to the current element context.
    if tag.stack != []:
        tag.stack[-1].dom_element.addEventListener(event, create_proxy(listener))

def create_tag(tag_name, namespace = None):
    """
    Creats a tag with the tag_name, and returns it.
    """
    def f(content = None, **attrs):
        return tag(tag_name, content, namespace, **attrs)
    return f

def bind_tag(tag_name, namespace = None):
    """
    Creates a tag with the tag_name, and binds it to a module variable with the same name as the tag.
    """
    globals()[tag_name] = create_tag(tag_name, namespace)

# Concrete HTML and SVG tags
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

for t in html_tags.split(" "):
    bind_tag(t)

for t in svg_tags.split(" "):
    bind_tag(t, "http://www.w3.org/2000/svg")

# Special treatment for some tags whose name collide with Python symbols
input_ = create_tag("input")
set_ = create_tag("set")