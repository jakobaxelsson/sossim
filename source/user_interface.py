"""
User interface for the SoSSim system-of-systems simulator.
The user interface is based on the Model-View-Controller pattern.
The model is a Mesa model, and this module provides simulation controller and user interface elements.
The user interface is provided as HTML DOM elements which is manipulated using the domscript module.
"""
from typing import Any

import js #type: ignore
from pyodide.ffi import create_proxy #type: ignore

from agent import Vehicle
from configuration import Configuration
from domscript import event_listener, br, button, circle, details, document, div, g, h3, input_, label, li, line, main, nav, p, polygon, rect, span, summary, svg, ul #type: ignore
from model import TransportSystem
from space import RoadNetworkGrid
from view import View

class VehicleView(View):
    """
    Renders a vehicle on the map.
    """
    # Add a vehicle which can be selected by clicking on it, and display detailed information about it.
    selected_vehicle_id = None

    def __init__(self, agent: Vehicle):
        """
        Draws the vehicle in its initial position.
        The size of the vehicle reflects its load capacity.
        The rotation reflects its heading.
        It is assigned a random color, to makes it easier to follow a specific vehicle on the screen.

        Args:
            agent (Vehicle): the agent which the view is connected to.
        """
        self.agent = agent

        # Draw the vehicle
        self.color = "#" + "".join([agent.model.random.choice(list("0123456789abcdef")) for i in range(6)])
        (x, y) = agent.pos
        with document.query("#vehicles"):
            with g(id = f"vehicle_{agent.unique_id}", transform = f"translate({x + 0.5}, {y + 0.5}) rotate({agent.heading})"): 
                height = (agent.capacity + 1) / (agent.max_load + 1) * 0.8
                rect(x = -0.2, y = -height / 2, width = 0.4, height = height, fill = self.color)
                # When a vehicle is clicked, print some data about it to the console.
                event_listener("click", lambda _: self.select_vehicle())

    def select_vehicle(self):
        """
        Selects a vehicle.
        """
        VehicleView.selected_vehicle_id = self.agent.unique_id
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
            with document.query("#agent_information", clear = True):
                h3("Agent information")
                attributes = ["unique_id", "pos", "energy_level", "plan"]
                for a in attributes:
                    p(f"{a}: {getattr(agent, a)}")

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
        with document.query("#road_network", clear = True):
            # Visualize roads
            for (x1, y1), (x2, y2) in space.road_edges():
                line(cls = "road", x1 = x1 + 0.5, y1 = y1 + 0.5, x2 = x2 + 0.5, y2 = y2 + 0.5, 
                     stroke_width = 0.8, stroke_linecap = "round")
            # Visualize destinations
            for node in space.road_nodes():                
                (x, y) = node
                if space.is_destination(node):
                    circle(cls = "destination", cx =  0.5, cy = 0.5, r = 0.25, transform = f"translate({x}, {y})")
            # Visualize charging points
            for node in space.road_nodes():                
                (x, y) = node
                if space.is_charging_point(node):
                    with g(cls = "charging_point", transform = f"translate({x}, {y})"):
                        circle(cx =  0.5, cy = 0.5, r = 0.25)
                        polygon(points = "0.52,0.30 0.35,0.55 0.48,0.55 0.48,0.70 0.65,0.45 0.52,0.45 0.52,0.30")

class TransportSystemView(View):
    """
    Provides a view of the entire transport system.
    """
    def __init__(self, model: TransportSystem):
        """
        Initiates the view of the model, which consists of a map, vehicles, and simulation controls.
        """
        # Add a space view.
        model.space.add_view(RoadNetworkGridView())

        # Add agent views
        document.query("#vehicles", clear = True)
        for agent in model.schedule.agents:
            if isinstance(agent, Vehicle):
                agent.add_view(VehicleView(agent))

    def update(self, model: TransportSystem):
        """
        Updates the time indicator in the user interface.

        Args:
            model (TransportSystem): the model.
        """
        t = model.schedule.time
        with document.query("#time") as p:
            p.inner_html(t)

async def open_file() -> str:
    """
    Opens the file picker dialog and reads the content of the file selected by the user.

    Returns:
        str | None: the content of the file, or None if file reading failed.
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
        """
        self.ui = ui
        self.timer = None
        self.zoom_level = 1.0
        # The panning state is calculated for the center of the map to make zooming perform correctly
        # Note that width and height are here in the coarse network units, so multiply by 4 everywhere
        self.pan_x = self.ui.model.space.width  * 4 / 2
        self.pan_y = self.ui.model.space.height * 4 / 2
        with document.query("#controls", clear = True):
            with div(id = "simulation_controls"):
                with button("Step"):
                    event_listener("click", lambda _: self.ui.model.step())
                with button("Run"):
                    event_listener("click", lambda _: self.run())
                with button("Stop"):
                    event_listener("click", lambda _: self.stop())
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
        
    def run(self):
        """
        Runs the simulation by repeatedly invoking step (with a small delay between steps).
        """
        self.timer = js.setInterval(create_proxy(self.ui.model.step), 250)

    def stop(self):
        """
        Stops a running simulation.
        """
        if self.timer:
            js.clearInterval(self.timer)

    def transform_map(self, zoom: float = 1.0, x: int = 0, y: int = 0):
        """
        Zooms the map by the zoom factor, and translates it by x, y for panning.

        Args:
            zoom (int, optional): factor by which the current zoom level is increased. Defaults to 0.
            x (int, optional): translation in x dimension. Defaults to 0.
            y (int, optional): translation in y dimension. Defaults to 0.
        """
        self.zoom_level *= zoom
        self.pan_x -= 4 * x
        self.pan_y -= 4 * y
        offset_x = -self.pan_x + self.ui.model.space.width  * 4 / 2 / self.zoom_level
        offset_y = -self.pan_y + self.ui.model.space.height * 4 / 2 / self.zoom_level
        with document.query("#map_content") as m:
            m["transform"] = f"scale({self.zoom_level}) translate({offset_x} {offset_y})"
            print(f"scale({self.zoom_level}) translate({offset_x} {offset_y})")

class ConfigurationController:
    """
    Provides a model configuration controller that lets the user configure the model.
    """
    def __init__(self, ui: "UserInterface"):
        """
        Sets up the configuration controller, adding the necessary DOM elements.
        """
        self.ui = ui
        self.update()

    def update(self):
        """
        Updates the configuration controller to match the current configuration.
        """
        with document.query("#configuration", clear = True):
            h3("Configuration parameters")
            with div(id = "configuration_controls", cls = "flex demo"):
                for cls, params in self.ui.configuration.data.items():
                    with details(id = "configuration_" + cls):
                        summary(cls)
                        for p, v in params.items():
                            # Add a label with the parameter name, and the help text as a tooltip
                            label(p, title = self.ui.configuration.params[cls][p]["help"])
                            br()
                            input_(id = p, value = v) 
                            br()
                with button("Generate", cls = "error"):
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
                        if field.dom_element.value != "":
                            self.ui.configuration.set_param_value(cls, p, param_type(field.dom_element.value))
        # Reinitialize the model and its views.
        self.ui.model.__init__(self.ui.configuration)
        self.ui.model.clear_views()
        self.ui.model.add_view(TransportSystemView(self.ui.model))
        self.ui.simulation_controller.__init__(self.ui)
        with document.query("#random_seed") as field:
            field.dom_element.value = self.ui.model.random_seed

class MenuBar:
    """
    Main menu bar of the SoSSim user interface.
    """
    def __init__(self, ui: "UserInterface"):
        self.ui = ui
        with nav(id = "menubar"):
            with ul():
                with li("File"):
                    with ul():
                        with li("Open configuration..."):
                            event_listener("click", self.open_configuration)
                        with li("Save configuration as..."):
                            event_listener("click", self.save_configuration)
                with li("View"):
                    with ul():
                        with li("Configuration"):
                            event_listener("click", lambda _: self.select_content("#configuration"))
                        with li("Agent"):
                            event_listener("click", lambda _: self.select_content("#agent_information"))
                with li("About"):
                    # Open the project README file on Github in a separate tab.
                    about_page = "https://github.com/jakobaxelsson/sossim/blob/master/README.md"
                    event_listener("click", lambda _: js.window.open(about_page, "_blank"))

    def select_content(self, id: str):
        """
        Selects what to show on the right side of the screen.

        Args:
            id (str): the id of the element to be shown.
        """
        # Hide all content elements.
        for element in document.query("#content").dom_element.children:
            element.style.display = "none"

        # Show the selected content element.
        document.query(id).dom_element.style.display = "block"

    async def open_configuration(self, event: Any):
        """
        Event handler for the open configuration menu item.

        Args:
            event (Any): the event (not used).
        """
        try:
            data = await open_file()
            self.ui.configuration.from_json(data)

            # Reinitialize the model and its views.
            self.ui.model.__init__(self.ui.configuration)
            self.ui.model.clear_views()
            self.ui.model.add_view(TransportSystemView(self.ui.model))
            self.ui.configuration_controller.update()
        except Exception as e:
            print("Open configuration failed with exception:", e)

    async def save_configuration(self, event: Any):
        """
        Event handler for the save configuration as menu item.

        Args:
            event (Any): the event (not used).
        """
        try:
            content = self.ui.configuration.to_json()
            await save_file_as(content)
        except Exception as e:
            print("Save configuration as failed with exception:", e)

class UserInterface:
    """
    Creates the user interface of the SoSSim interactive mode.
    """
    def __init__(self, model: TransportSystem, configuration: Configuration):
        self.model = model
        self.configuration = configuration

        # Remove load message and set cursor to default
        with document.query("#load_msg") as e:
            e.remove()
        with document.query("body") as b:
            b["style"] = "cursor: default;"
        # Setup main layout
        with document.query("body"):
            MenuBar(self)
            with main():
                with div(id = "main_grid", style = "display: grid; grid-template-columns: 2fr 1fr;"):
                    with div(id = "simulation"):
                        div(id = "controls")
                        with svg(cls = "map", id = "map", width = "100%", height = "90vh"):
                            with g(id = "map_content"):
                                g(id = "road_network")
                                g(id = "vehicles")
                        self.simulation_controller = SimulationController(self)
                    with div(id = "content"):
                        with div(id = "configuration"):
                            self.configuration_controller = ConfigurationController(self)
                        with div(id = "agent_information", style = "display: none;"):
                            h3("Agent information")
                            p("Select an agent to display information about it")
        model.add_view(TransportSystemView(model))