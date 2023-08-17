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
    children: list[Self]
    firstChild: Self
    innerHTML: str
    style: Any

    def addEventListener(self, event: str, listener: Callable[[Event], Any]): ...
    def appendChild(self, child: Self): ...
    def querySelector(self, q: str) -> Self: ...
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

if sys.platform == "emscripten":
    import js
    from pyodide.ffi import create_proxy
else:
    # Specifies the interface of the Pyodide entities js and create_proxy, for typechecking.
    class js(Protocol):
        document: JSDocument

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

    def __getitem__(self, attribute: str) -> str:
        """
        Retrieves an attribute of the DOM element.

        Args:
            attribute (str): the attribute.

        Returns:
            str: returns the attribute value as a string.
        """
        return self.dom_element.getAttribute(attribute)      

    def __setitem__(self, attribute: str, value: Any):
        """
        Changes an attribute of the DOM element.

        Args:
            attribute (str): the attribute.
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

    def visible(self, is_visible: bool = True):
        """
        Changes the visibility of the element.

        Args:
            is_visible (bool, optional): if True, the element becomes visible, and otherwise invisible. Defaults to True.
        """
        self.dom_element.style.display = "block" if is_visible else "none"

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

# Concrete HTML tags
# Tag names that are reserved words in Python have an underscore appended.
# I.e., del becomes del_, input becomes input_, and set becomes set_.

a = create_tag("a")
abbr = create_tag("abbr")
acronym = create_tag("acronym")
address = create_tag("address")
applet = create_tag("applet")
area = create_tag("area")
article = create_tag("article")
aside = create_tag("aside")
audio = create_tag("audio")
b = create_tag("b")
base = create_tag("base")
basefont = create_tag("basefont")
bdi = create_tag("bdi")
bdo = create_tag("bdo")
big = create_tag("big")
blockquote = create_tag("blockquote")
body = create_tag("body")
br = create_tag("br")
button = create_tag("button")
canvas = create_tag("canvas")
caption = create_tag("caption")
center = create_tag("center")
cite = create_tag("cite")
code = create_tag("code")
col = create_tag("col")
colgroup = create_tag("colgroup")
data = create_tag("data")
datalist = create_tag("datalist")
dd = create_tag("dd")
del_ = create_tag("del")
details = create_tag("details")
dfn = create_tag("dfn")
dialog = create_tag("dialog")
dir = create_tag("dir")
div = create_tag("div")
dl = create_tag("dl")
dt = create_tag("dt")
em = create_tag("em")
embed = create_tag("embed")
fieldset = create_tag("fieldset")
figcaption = create_tag("figcaption")
figure = create_tag("figure")
font = create_tag("font")
footer = create_tag("footer")
form = create_tag("form")
frame = create_tag("frame")
frameset = create_tag("frameset")
h1 = create_tag("h1")
h2 = create_tag("h2")
h3 = create_tag("h3")
h4 = create_tag("h4")
h5 = create_tag("h5")
h6 = create_tag("h6")
head = create_tag("head")
header = create_tag("header")
hr = create_tag("hr")
html = create_tag("html")
i = create_tag("i")
iframe = create_tag("iframe")
img = create_tag("img")
input_ = create_tag("input")
ins = create_tag("ins")
kbd = create_tag("kbd")
label = create_tag("label")
legend = create_tag("legend")
li = create_tag("li")
link = create_tag("link")
main = create_tag("main")
map = create_tag("map")
mark = create_tag("mark")
meta = create_tag("meta")
meter = create_tag("meter")
nav = create_tag("nav")
noframes = create_tag("noframes")
noscript = create_tag("noscript")
object = create_tag("object")
ol = create_tag("ol")
optgroup = create_tag("optgroup")
option = create_tag("option")
output = create_tag("output")
p = create_tag("p")
param = create_tag("param")
picture = create_tag("picture")
pre = create_tag("pre")
progress = create_tag("progress")
q = create_tag("q")
rp = create_tag("rp")
rt = create_tag("rt")
ruby = create_tag("ruby")
s = create_tag("s")
samp = create_tag("samp")
script = create_tag("script")
section = create_tag("section")
select = create_tag("select")
set_ = create_tag("set")
small = create_tag("small")
source = create_tag("source")
span = create_tag("span")
strike = create_tag("strike")
strong = create_tag("strong")
style = create_tag("style")
sub = create_tag("sub")
summary = create_tag("summary")
sup = create_tag("sup")
svg = create_tag("svg")
table = create_tag("table")
tbody = create_tag("tbody")
td = create_tag("td")
template = create_tag("template")
textarea = create_tag("textarea")
tfoot = create_tag("tfoot")
th = create_tag("th")
thead = create_tag("thead")
time = create_tag("time")
title = create_tag("title")
tr = create_tag("tr")
track = create_tag("track")
tt = create_tag("tt")
u = create_tag("u")
ul = create_tag("ul")
var = create_tag("var")
video = create_tag("video")
wbr = create_tag("wbr")

# Concrete SVG tags
# Hyphens in the tag names are replaced by underscore in the Python variable name.

altGlyph = create_tag("altGlyph", "http://www.w3.org/2000/svg")
altGlyphDef = create_tag("altGlyphDef", "http://www.w3.org/2000/svg")
altGlyphItem = create_tag("altGlyphItem", "http://www.w3.org/2000/svg")
animate = create_tag("animate", "http://www.w3.org/2000/svg")
animateColor = create_tag("animateColor", "http://www.w3.org/2000/svg")
animateMotion = create_tag("animateMotion", "http://www.w3.org/2000/svg")
animateTransform = create_tag("animateTransform", "http://www.w3.org/2000/svg")
circle = create_tag("circle", "http://www.w3.org/2000/svg")
clipPath = create_tag("clipPath", "http://www.w3.org/2000/svg")
color_profile = create_tag("color-profile", "http://www.w3.org/2000/svg")
cursor = create_tag("cursor", "http://www.w3.org/2000/svg")
defs = create_tag("defs", "http://www.w3.org/2000/svg")
desc = create_tag("desc", "http://www.w3.org/2000/svg")
ellipse = create_tag("ellipse", "http://www.w3.org/2000/svg")
feBlend = create_tag("feBlend", "http://www.w3.org/2000/svg")
feColorMatrix = create_tag("feColorMatrix", "http://www.w3.org/2000/svg")
feComponentTransfer = create_tag("feComponentTransfer", "http://www.w3.org/2000/svg")
feComposite = create_tag("feComposite", "http://www.w3.org/2000/svg")
feConvolveMatrix = create_tag("feConvolveMatrix", "http://www.w3.org/2000/svg")
feDiffuseLighting = create_tag("feDiffuseLighting", "http://www.w3.org/2000/svg")
feDisplacementMap = create_tag("feDisplacementMap", "http://www.w3.org/2000/svg")
feDistantLight = create_tag("feDistantLight", "http://www.w3.org/2000/svg")
feFlood = create_tag("feFlood", "http://www.w3.org/2000/svg")
feFuncA = create_tag("feFuncA", "http://www.w3.org/2000/svg")
feFuncB = create_tag("feFuncB", "http://www.w3.org/2000/svg")
feFuncG = create_tag("feFuncG", "http://www.w3.org/2000/svg")
feFuncR = create_tag("feFuncR", "http://www.w3.org/2000/svg")
feGaussianBlur = create_tag("feGaussianBlur", "http://www.w3.org/2000/svg")
feImage = create_tag("feImage", "http://www.w3.org/2000/svg")
feMerge = create_tag("feMerge", "http://www.w3.org/2000/svg")
feMergeNode = create_tag("feMergeNode", "http://www.w3.org/2000/svg")
feMorphology = create_tag("feMorphology", "http://www.w3.org/2000/svg")
feOffset = create_tag("feOffset", "http://www.w3.org/2000/svg")
fePointLight = create_tag("fePointLight", "http://www.w3.org/2000/svg")
feSpecularLighting = create_tag("feSpecularLighting", "http://www.w3.org/2000/svg")
feSpotLight = create_tag("feSpotLight", "http://www.w3.org/2000/svg")
feTile = create_tag("feTile", "http://www.w3.org/2000/svg")
feTurbulence = create_tag("feTurbulence", "http://www.w3.org/2000/svg")
filter = create_tag("filter", "http://www.w3.org/2000/svg")
font = create_tag("font", "http://www.w3.org/2000/svg")
font_face = create_tag("font-face", "http://www.w3.org/2000/svg")
font_face_format = create_tag("font-face-format", "http://www.w3.org/2000/svg")
font_face_name = create_tag("font-face-name", "http://www.w3.org/2000/svg")
font_face_src = create_tag("font-face-src", "http://www.w3.org/2000/svg")
font_face_uri = create_tag("font-face-uri", "http://www.w3.org/2000/svg")
foreignObject = create_tag("foreignObject", "http://www.w3.org/2000/svg")
g = create_tag("g", "http://www.w3.org/2000/svg")
glyph = create_tag("glyph", "http://www.w3.org/2000/svg")
glyphRef = create_tag("glyphRef", "http://www.w3.org/2000/svg")
hkern = create_tag("hkern", "http://www.w3.org/2000/svg")
image = create_tag("image", "http://www.w3.org/2000/svg")
line = create_tag("line", "http://www.w3.org/2000/svg")
linearGradient = create_tag("linearGradient", "http://www.w3.org/2000/svg")
marker = create_tag("marker", "http://www.w3.org/2000/svg")
mask = create_tag("mask", "http://www.w3.org/2000/svg")
metadata = create_tag("metadata", "http://www.w3.org/2000/svg")
missing_glyph = create_tag("missing-glyph", "http://www.w3.org/2000/svg")
mpath = create_tag("mpath", "http://www.w3.org/2000/svg")
path = create_tag("path", "http://www.w3.org/2000/svg")
pattern = create_tag("pattern", "http://www.w3.org/2000/svg")
polygon = create_tag("polygon", "http://www.w3.org/2000/svg")
polyline = create_tag("polyline", "http://www.w3.org/2000/svg")
radialGradient = create_tag("radialGradient", "http://www.w3.org/2000/svg")
rect = create_tag("rect", "http://www.w3.org/2000/svg")
solidColor = create_tag("solidColor", "http://www.w3.org/2000/svg")
stop = create_tag("stop", "http://www.w3.org/2000/svg")
style = create_tag("style", "http://www.w3.org/2000/svg")
svg = create_tag("svg", "http://www.w3.org/2000/svg")
switch = create_tag("switch", "http://www.w3.org/2000/svg")
symbol = create_tag("symbol", "http://www.w3.org/2000/svg")
text = create_tag("text", "http://www.w3.org/2000/svg")
textPath = create_tag("textPath", "http://www.w3.org/2000/svg")
title = create_tag("title", "http://www.w3.org/2000/svg")
tref = create_tag("tref", "http://www.w3.org/2000/svg")
tspan = create_tag("tspan", "http://www.w3.org/2000/svg")
use = create_tag("use", "http://www.w3.org/2000/svg")
view = create_tag("view", "http://www.w3.org/2000/svg")
vkern = create_tag("vkern", "http://www.w3.org/2000/svg")