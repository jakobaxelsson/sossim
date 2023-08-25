"""
User interface for the SoSSim system-of-systems simulator.
The user interface is based on the Model-View-Controller pattern.
The module provides simulation controller and user interface elements, as well as views for different model elements.
The user interface is provided as HTML DOM elements which is manipulated using the domed package.
"""
from typing import Any

import js # type: ignore
from pyodide.ffi import create_proxy # type: ignore

from configuration import Configuration
from domed.core import create_tag, event_listener, document
from domed.html import br, button, details, div, h3, input_, label, li, main, nav, p, span, style, summary, svg, ul
from domed.svg import circle, defs, g, line, path, polygon, rect, svg
from entities import Cargo, Vehicle
from model import TransportSystem
from space import RoadNetworkGrid
from view import View

class VehicleView(View):
    """
    Renders a vehicle on the map.
    """
    # Add a vehicle which can be selected by clicking on it, and display detailed information about it.
    selected_vehicle_id = None

    def __init__(self, ui: "UserInterface", agent: Vehicle):
        """
        Draws the vehicle in its initial position.
        The size of the vehicle reflects its load capacity.
        The rotation reflects its heading.
        It is assigned a random color, to makes it easier to follow a specific vehicle on the screen.

        Args:
            ui (UserInterface): the user interface of which this view is a part.
            agent (Vehicle): the agent which the view is connected to.
        """
        self.ui = ui
        self.agent = agent

        # Draw the vehicle in a random color to make it easy to distinguish them.
        self.color = "#" + "".join([agent.random.choice(list("0123456789abcdef")) for i in range(6)])
        (x, y) = agent.pos
        with document.query("#vehicles"):
            with g(id = f"vehicle_{agent.unique_id}", transform = f"translate({x + 0.5}, {y + 0.5}) rotate({agent.heading})"): 
                height = (agent.capacity + 1) / (agent.max_load + 1) * 0.8
                rect(x = -0.2, y = -height / 2, width = 0.4, height = height, fill = self.color)
                # When a vehicle is clicked, print some data about it to the console.
                event_listener("click", lambda _: self.select_vehicle())

    def select_vehicle(self):
        """
        Selects a vehicle and show its information.
        If the selected vehicle is selected again, it is deselected.
        """
        if VehicleView.selected_vehicle_id == self.agent.unique_id:
            VehicleView.selected_vehicle_id = None
            document.query("#route").clear()
            document.query("#world_model").clear()
        else:
            VehicleView.selected_vehicle_id = self.agent.unique_id
            self.ui.show_but_hide_siblings("#agent_information")
        self.update(self.agent)

    def update(self, agent: Vehicle):
        """
        Updates the position ahd heading of the vehicle by translating and rotating the SVG elements.

        Args:
            agent (Vehicle): the agent model which the view is connected to.
        """
        # Update vehicle positions
        (x, y) = agent.pos
        with document.query(f"#vehicle_{agent.unique_id}") as g:
            g["transform"] = f"translate({x + 0.5}, {y + 0.5}) rotate({agent.heading})"

        # If this vehicle is selected, show its information
        if agent.unique_id == VehicleView.selected_vehicle_id:
            with document.query("#agent_information").clear():
                h3("Agent information")
                attributes = ["unique_id", "pos", "energy_level", "world_model", "cargos"]
                for a in attributes:
                    p(f"{a}: {getattr(agent, a)}")

            # Draw its planned route if it has one
            wm = agent.world_model
            if wm.plan and hasattr(wm.plan[0], "route"):
                route_nodes = wm.plan[0].route
                with document.query("#route").clear():
                    for (x1, y1), (x2, y2) in zip(route_nodes[0: -1], route_nodes[1:]):
                        line(cls = "route", x1 = x1 + 0.5, y1 = y1 + 0.5, x2 = x2 + 0.5, y2 = y2 + 0.5)
                            
            # Show its world view space if it has one
            with document.query("#world_model").clear():
                width = 4 * agent.model.space.width
                height = 4 * agent.model.space.height                      
                (x, y) = agent.pos
                dist = self.agent.perception_range
                path(cls = "world_model_space", fill_rule = "evenodd", 
                     d = f"M0,0 h{width} v{height} h-{width} z M{x - dist},{y - dist} v{2 * dist + 1} h{2 * dist + 1} v-{2 * dist + 1} z")

class CargoView(View):
    """
    Renders a cargo on the map.
    """
    def __init__(self, ui: "UserInterface", agent: Cargo):
        """
        Draws the cargo in its initial position.

        Args:
            ui (UserInterface): the user interface of which this view is a part.
            agent (Cargo): the agent which the view is connected to.
        """
        self.agent = agent

        # Draw the cargo as a circle.
        (x, y) = agent.pos
        with document.query("#cargos"):
            with g(cls = "cargo", id = f"cargo_{agent.unique_id}", transform = f"translate({x + 0.5}, {y + 0.5})"):
                circle(cx = 0, cy = 0, r = 0.15)

    def update(self, agent: Cargo):
        """
        Updates the position of the cargo.

        Args:
            agent (Cargo): the agent model which the view is connected to.
        """
        (x, y) = agent.pos
        with document.query(f"#cargo_{agent.unique_id}") as g:
            g["transform"] = f"translate({x + 0.5}, {y + 0.5})"

class RoadNetworkGridView(View):
    """
    Provides a view of the road network.
    """
    def update(self, space: RoadNetworkGrid):
        """
        Updates the map, clearing any previous graphics.
        When drawing the graphics, the internal scale in the SVG is one cell to one unit.
        The viewBox is set to the entire graph, and the graphics is scaled through SVG element styling.

        Args:
            model (TransportSystem): the transport system model to be reflected in the user interface.
        """
        with document.query("#map") as m:
            m["viewBox"] = f"0 0 {space.width * 4} {space.height * 4}"

        with document.query("#grid").clear():
            # Visualize the coarse grid
            for x in range(0, space.width + 1):
                line(cls = "grid_line", x1 = 4 * x, y1 = 0, x2 = 4 * x, y2 = 4 * space.height)
            for y in range(0, space.height + 1):
                line(cls = "grid_line", x1 = 0, y1 = 4 * y, x2 = 4 * space.width, y2 = 4 * y)

        with document.query("#coarse_road_network").clear():
            # Visualize roads
            for (x1, y1), (x2, y2) in space.coarse_network.edges:
                line(cls = "coarse_road", x1 = 4 * x1 + 2, y1 = 4 * y1 + 2, x2 = 4 * x2 + 2, y2 = 4 * y2 + 2)

        with document.query("#road_network").clear():
            # Visualize roads
            for (x1, y1), (x2, y2) in space.road_edges():
                line(cls = "road", x1 = x1 + 0.5, y1 = y1 + 0.5, x2 = x2 + 0.5, y2 = y2 + 0.5)

            # Placeholder for vehicle route information
            g(id = "route")

            # Visualize destinations and charging points.
            for node in space.road_nodes(space.is_destination):
                (x, y) = node
                if space.is_charging_point(node):
                    with g(cls = "charging_point", transform = f"translate({x}, {y})"):
                        circle(cx =  0.5, cy = 0.5, r = 0.25)
                        polygon(points = "0.52,0.30 0.35,0.55 0.48,0.55 0.48,0.70 0.65,0.45 0.52,0.45 0.52,0.30")
                else:
                    circle(cls = "destination", cx =  0.5, cy = 0.5, r = 0.25, transform = f"translate({x}, {y})")

class TransportSystemView(View):
    """
    Provides a view of the entire transport system.
    """
    def __init__(self, ui: "UserInterface"):
        """
        Initiates the view of the model, which consists of a map, vehicles, and simulation controls.

        Args:
            ui (UserInterface): the user interface of which this view is a part.
        """
        # Add a space view.
        ui.model.space.add_view(RoadNetworkGridView())

        # Add agent views
        document.query("#vehicles").clear()
        document.query("#cargos").clear()
        for agent in ui.model.agents():
            if isinstance(agent, Vehicle):
                agent.add_view(VehicleView(ui, agent))
            elif isinstance(agent, Cargo):
                agent.add_view(CargoView(ui, agent))

    def update(self, model: TransportSystem):
        """
        Updates the time indicator in the user interface.

        Args:
            model (TransportSystem): the model.
        """
        t = model.time()
        with document.query("#time") as p:
            p.inner_html(int(t))

async def open_file() -> str:
    """
    Opens the file picker dialog and reads the content of the file selected by the user.

    Returns:
        str: the content of the file.
    """
    file_handles = await js.window.showOpenFilePicker()
    file_handle = file_handles[0]
    file = await file_handle.getFile()
    data = await file.text()
    return data

async def save_file_as(data: str):
    """
    Opens the file picker dialog and saves the data to the file selected by the user.

    Args:
        data (str): the data to be saved.
    """
    file_handle = await js.window.showSaveFilePicker()
    writable = await file_handle.createWritable()
    await writable.write(data)
    await writable.close()

class SimulationController:
    """
    Provides a simulation controller that lets the user run a simulation.
    """
    def __init__(self, ui: "UserInterface"):
        """
        Sets up the simulation controller, adding the necessary DOM elements.

        Args:
            ui (UserInterface): the user interface of which this controller is a part.
        """
        self.ui = ui
        self.timer = None
        self.simulation_delay = 250.0 # Delay between simulation steps in milliseconds
        self.zoom_level = 1.0

        # The panning state is calculated for the center of the map to make zooming perform correctly
        self.pan_x = -self.ui.model.space.width / 2
        self.pan_y = -self.ui.model.space.height / 2
        with document.query("#controls").clear():
            with div(id = "simulation_controls"):
                with button("Step"):
                    event_listener("click", lambda _: self.step())
                with button("Run"):
                    event_listener("click", lambda _: self.run())
                with button("Stop"):
                    event_listener("click", lambda _: self.stop())
                with button("Slower"):
                    event_listener("click", lambda _: self.set_simulation_delay(2.0))
                with button("Faster"):
                    event_listener("click", lambda _: self.set_simulation_delay(0.5))
                span("Time: ")
                span("0", id = "time")
                with button("Zoom in"):
                    event_listener("click", lambda _: self.transform_map(zoom = 1.25))
                with button("Zoom out"):
                    event_listener("click", lambda _: self.transform_map(zoom = 0.8))
                with button("Left"):
                    event_listener("click", lambda _: self.transform_map(x = 1, y = 0))
                with button("Right"):
                    event_listener("click", lambda _: self.transform_map(x = -1, y = 0))
                with button("Up"):
                    event_listener("click", lambda _: self.transform_map(x = 0, y = 1))
                with button("Down"):
                    event_listener("click", lambda _: self.transform_map(x = 0, y = -1))
        self.transform_map()
        
    def step(self):
        """
        Executes one step of the simulation.
        """
        try:
            self.ui.model.step()
        except Exception as e:
            # If an exception occurs, stop any running simulation and reraise the exception
            self.stop()
            raise e

    def run(self):
        """
        Runs the simulation by repeatedly invoking step (with a small delay between steps).
        """
        self.timer = js.setInterval(create_proxy(self.step), self.simulation_delay)

    def stop(self):
        """
        Stops a running simulation.
        """
        if self.timer:
            js.clearInterval(self.timer)
            self.timer = None

    def set_simulation_delay(self, factor: float):
        """
        Changes the speed of the simulation run by a factor.

        Args:
            factor (int): the factor by which the simulation delay is multiplied.
        """
        self.simulation_delay = self.simulation_delay * factor
        # If the simulation is running, restart it with the new delay.
        if self.timer:
            self.stop()
            self.run()

    def transform_map(self, zoom: float = 1.0, x: int = 0, y: int = 0):
        """
        Zooms the map by the zoom factor, and translates it by x, y for panning.

        Args:
            zoom (int, optional): factor by which the current zoom level is increased. Defaults to 0.
            x (int, optional): translation in x dimension. Defaults to 0.
            y (int, optional): translation in y dimension. Defaults to 0.
        """
        self.zoom_level *= zoom
        self.pan_x += x
        self.pan_y += y
        offset_x = self.pan_x + self.ui.model.space.width  / 2 / self.zoom_level
        offset_y = self.pan_y + self.ui.model.space.height / 2 / self.zoom_level
        with document.query("#map_content") as m:
            # Note that width and height are coarse network units, so multiply by 4 to get offset in correct units
            m["transform"] = f"scale({self.zoom_level}) translate({4 * offset_x} {4 * offset_y})"

class ConfigurationController:
    """
    Provides a model configuration controller that lets the user configure the model.
    """
    def __init__(self, ui: "UserInterface"):
        """
        Sets up the configuration controller, adding the necessary DOM elements.

        Args:
            ui (UserInterface): the user interface of which this controller is a part.
        """
        self.ui = ui
        self.update()

    def update(self):
        """
        Updates the configuration controller to match the current configuration.
        """
        with document.query("#configuration").clear():
            h3("Configuration parameters")
            with div(id = "configuration_controls"):
                for cls, params in self.ui.configuration.data.items():
                    with details(id = "configuration_" + cls):
                        summary(cls)
                        for p, v in params.items():
                            # Add a label with the parameter name, and the help text as a tooltip
                            if self.ui.configuration.params[cls][p]["type"] == bool:
                                # Boolean params are shown as a checkbox with a label
                                with input_(id = p, type = "checkbox") as checkbox:
                                    if self.ui.configuration.data[cls][p]:
                                        checkbox["checked"] = "" # Empty string means that it will appear as checked
                                label(p)
                            else:
                                # Non-boolean params are shown as a label and an input field
                                label(p, title = self.ui.configuration.params[cls][p]["help"])
                                input_(id = p, value = v) 
                with button("Generate", title = "Generates a new model based on the provided configuration parameters"):
                    event_listener("click", lambda _: self.generate())
        with document.query("#random_seed") as field:
            field.dom_element.value = self.ui.model.random_seed

    def generate(self):
        """
        Generates a new model based on parameter values in the input fields in the simulation controls.
        If no value is provided, the default parameter value is used instead.
        """
        for cls, params in self.ui.configuration.data.items():
                for p, _ in params.items():
                    with document.query("#" + p) as field:
                        param_type = self.ui.configuration.params[cls][p]["type"]
                        if param_type == bool:
                            self.ui.configuration.set_param_value(cls, p, field.dom_element.checked)
                        else:
                            if field.dom_element.value != "":
                                self.ui.configuration.set_param_value(cls, p, param_type(field.dom_element.value))
        self.ui.reinitialize()

class ViewController:
    """
    Provides a view configuration controller that lets the user configure what simulation elements are to be visible.
    """
    def __init__(self, ui: "UserInterface"):
        """
        Sets up the view controller, adding the necessary DOM elements.

        Args:
            ui (UserInterface): the user interface of which this controller is a part.
        """
        self.ui = ui
        self.update()

    def update(self):
        """
        Updates the view controller to match the current settings.
        """
        with document.query("#view_settings").clear():
            h3("View settings")
            self.add_control("Grid", "#grid")
            self.add_control("Coarse road network", "#coarse_road_network")
            self.add_control("Road network", "#road_network")
            self.add_control("World model", "#world_model")
            self.add_control("Route", "#route")
            self.add_control("Vehicles", "#vehicles")
            self.add_control("Cargo", "#cargos")

    def add_control(self, label_str: str, q: str, checked: bool = True):
        """
        Creates a checkbox that can be used to toggle visibility of an element.

        Args:
            label_str (str): a label to be attached to the checkbox.
            q (str): a query string that gives the element whose visibility is controlled by the checkbox.
            checked (bool): if true, the checkbox is initially checked.
        """
        # TODO: It would be nicer if the initial checkbox status was derived from element being controlled
        with div():
            with input_(type = "checkbox") as checkbox:
                if checked:
                    checkbox["checked"] = "" # Empty string means that it will appear as checked
                event_listener("change", lambda event: document.query(q).visible(event.target.checked))
            label(label_str)

class MenuBar:
    """
    Main menu bar of the SoSSim user interface.
    """
    def __init__(self, ui: "UserInterface"):
        """
        Creates the main menu bar of the user interface.

        Args:
            ui (UserInterface): the user interface of which this element is a part.
        """
        self.ui = ui
        with nav(id = "menubar"):
            with ul():
                with li("File"):
                    with ul():
                        with li("Open configuration..."):
                            event_listener("click", self.open_configuration)
                        with li("Save configuration as..."):
                            event_listener("click", self.save_configuration)
                        with li("Save map as SVG..."):
                            event_listener("click", self.save_map_as_SVG)
                with li("View"):
                    with ul():
                        with li("Configuration"):
                            event_listener("click", self.show_content("#configuration"))
                        with li("Agent state"):
                            event_listener("click", self.show_content("#agent_information"))
                        with li("View settings"):
                            event_listener("click", self.show_content("#view_settings"))
                        with li("Python REPL"):
                            event_listener("click", self.show_content("#py-repl"))
                        with li("Collected data"):
                            event_listener("click", self.show_collected_data)
                with li("About"):
                    # Open the project README file on Github in a separate tab.
                    about_page = "https://github.com/jakobaxelsson/sossim/blob/master/README.md"
                    event_listener("click", lambda _: js.window.open(about_page, "_blank"))

    def show_content(self, q: str):
        """
        Returns an event handler that makes the main layout grid with map and content visible.
        The content is determined by the provided query string.

        Args:
            q (str): a query string determining which content to show.
        """
        def handler(event):
            self.ui.show_but_hide_siblings("#simulation_view")
            self.ui.show_but_hide_siblings(q)
        return handler

    def show_collected_data(self, event: Any):
        """
        Event handler for the show collected data menu item.

        Args:
            event (Any): the event (not used).
        """
        if self.ui.model.data_collector:
            with document.query("#collected_data").clear() as cd:
                html_text = self.ui.model.data_collector.get_agent_vars_dataframe().to_html()
                element = js.DOMParser.new().parseFromString(html_text, "text/html").body.firstChild
                cd.dom_element.appendChild(element)
            self.ui.show_but_hide_siblings("#data_view")

    async def open_configuration(self, event: Any):
        """
        Event handler for the open configuration menu item.

        Args:
            event (Any): the event (not used).
        """
        try:
            data = await open_file()
            self.ui.configuration.from_json(data)
            self.ui.reinitialize()
        except:
            pass

    async def save_configuration(self, event: Any):
        """
        Event handler for the save configuration as menu item.

        Args:
            event (Any): the event (not used).
        """
        try:
            content = self.ui.configuration.to_json()
            await save_file_as(content)
        except:
            pass

    async def save_map_as_SVG(self, event: Any):
        """
        Event handler for the save map as SVG menu item.

        Args:
            event (Any): the event (not used).
        """
        try:
            # Extract the CSS style information from the document
            style_information = "\n".join([rule.cssText for sheet in js.document.styleSheets for rule in sheet.cssRules])
            with document.query("#map") as m:
                # Serialize the clone tree as a string in XML format
                content = js.XMLSerializer.new().serializeToString(m.dom_element)

                # Prepend the content with the proper doctype
                doctype = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
                content = doctype + content

                # Insert style information, properly wrapped as CDATA.
                content = content.replace("</style>", f"<![CDATA[{style_information}]]></style>")

                # Let the user select a file, and save the content prepende with the doctype
                await save_file_as(content)
        except:
            pass

class UserInterface:
    """
    Creates the user interface of the SoSSim interactive mode.
    """
    def __init__(self, model: TransportSystem, configuration: Configuration):
        """
        Creates the user interface.

        Args:
            model (TransportSystem): the model being simulated.
            configuration (Configuration): the configuration object used to generate the model.
        """
        self.model = model
        self.configuration = configuration

        # Remove load message and set cursor to default
        with document.query("#load_msg") as e:
            e.remove()
        with document.query("body") as b:
            b["style"] = "cursor: default;"
        # Setup main layout
        with document.query("body"):
            self.menu_bar = MenuBar(self)
            with main():
                with div(id = "simulation_view"):
                    with div(id = "main_grid"):
                        with div(id = "simulation"):
                            div(id = "controls")
                            with svg(cls = "map", id = "map", width = "100%", height = "90vh"):
                                with g(id = "map_content"):
                                    # Placeholders for adding style information when exporting SVG to file
                                    with defs():
                                        style(type = "text/css")
                                    # Layers of map content, that can be shown or hidden separately
                                    g(id = "grid")
                                    g(id = "coarse_road_network")
                                    g(id = "road_network")
                                    g(id = "world_model")
                                    g(id = "vehicles")
                                    g(id = "cargos")
                            self.simulation_controller = SimulationController(self)
                        with div(id = "content"):
                            with div(id = "configuration"):
                                self.configuration_controller = ConfigurationController(self)
                            with div(id = "agent_information", style = "display: none;"):
                                h3("Agent information")
                                p("Select an agent to display information about it")
                            with div(id = "view_settings", style = "display: none;"):
                                self.view_controller = ViewController(self)
                            create_tag("py-repl")(id = "py-repl", style = "display: none;")
                with div(id = "data_view", stype = "display: none;"):
                    with div(id = "collected_data"):
                        p("Generate a model with data collection enabled to view data")
        model.add_view(TransportSystemView(self))

    def show_but_hide_siblings(self, q: str):
        """
        Shows the element that matches the query string q, while hiding all its direct siblings.

        Args:
            q (str): a query string that yields the element to be shown.
        """
        # Hide all siblings of the selected element
        for element in document.query(q).dom_element.parentElement.children:
            element.style.display = "none"

        # Show the selected element
        document.query(q).visible(True)

    def reinitialize(self):
        """
        Reinitialize the model and its views.
        """
        self.model.__init__(self.configuration)
        self.model.clear_views()
        self.model.add_view(TransportSystemView(self))
        self.configuration_controller.update()