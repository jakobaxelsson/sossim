"""
User interface for the SoSSim system-of-systems simulator.
The user interface is based on the Model-View-Controller pattern.
The model is a Mesa model, and this module provides simulation controller and user interface elements.
The user interface is provided as HTML DOM elements which is manipulated using the domscript module.
"""

import random

import js #type: ignore
from pyodide.ffi import create_proxy #type: ignore

import mesa

from configuration import Configuration
from agent import Vehicle
from model import TransportSystem
from domscript import add_event_listener, br, button, circle, dom, div, g, h3, input_, label, line, main, rect, span, svg #type: ignore

class SimulationController:
    """
    Provides a simulation controller that lets the user configure and run a simulation.
    """
    def __init__(self, model):
        """
        Sets up the simulation controller, adding the necessary DOM elements.
        """
        self.model = model
        self.timer = None
        with dom().query("#controls"):
            with div(id = "simulation_controls"):
                with button("Step"):
                    add_event_listener("click", lambda _: self.model.step())
                with button("Run"):
                    add_event_listener("click", lambda _: self.run())
                with button("Stop"):
                    add_event_listener("click", lambda _: self.stop())
                span("Time: ")
                span("0", id = "time")
        
    def run(self):
        """
        Runs the simulation by repeatedly invoking step (with a small delay between steps).
        """
        self.timer = js.setInterval(create_proxy(self.model.step), 250)

    def stop(self):
        """
        Stops a running simulation.
        """
        if self.timer:
            js.clearInterval(self.timer)

class ConfigurationController:
    """
    Provides a model configuration controller that lets the user configure the model.
    """
    def __init__(self, model, configuration: Configuration):
        """
        Sets up the configuration controller, adding the necessary DOM elements.
        """
        self.model = model
        self.configuration = configuration
        with dom().query("#configuration"):
            with div(id = "configuration_controls", cls = "flex demo"):
                for cls, params in self.configuration.data.items():
                    with div(id = "configuration_" + cls):
                        h3(cls)
                        for p, v in params.items():
                            label(p)
                            br()
                            input_(id = p, value = v) 
                            br()
                with button("Generate", cls = "error"):
                    add_event_listener("click", lambda _: self.generate())

    def generate(self):
        """
        Generates a new model based on parameter values in the input fields in the simulation controls.
        If no value is provided, the default parameter value is used instead.
        """
        for cls, params in self.configuration.data.items():
                for p, _ in params.items():
                    with dom().query("#" + p) as field:
                        param_type = self.configuration.params[cls][p]["type"]
                        if field.dom_element.value != "":
                            self.configuration.set_param_value(cls, p, param_type(field.dom_element.value))
        # Reinitialize the model, but keep its old view.
        self.model.__init__(self.configuration, self.model.view)
        with dom().query("#random_seed") as field:
            field.dom_element.value = self.model.random_seed

class AgentView: 
    """
    A common superclass for agent views.
    """
    pass

class VehicleView(AgentView):
    """
    Renders a vehicle on the map.
    """
    def __init__(self, agent: Vehicle):
        """
        Draws the vehicle in its initial position.
        The size of the vehicle reflects its load capacity.
        The rotation reflects its heading.
        It is assigned a random color, to makes it easier to follow a specific vehicle on the screen.

        Args:
            model (Vehicle): the agent model which the view is connected to.
        """
        # Draw the vehicle
        self.color = "#" + "".join([random.choice(list("0123456789abcdef")) for i in range(6)])
        (x, y) = agent.pos
        with dom().query("#vehicles"):
            rotation = { "N" : 0, "E" : 90, "S" : 180, "W" : 270 }
            with g(id = f"vehicle_{agent.unique_id}", transform = f"translate({x + 0.5}, {y + 0.5}) rotate({rotation[agent.heading]})"): 
                # TODO: Modify graphics to take max_load of vehicle into account
                rect(x = -0.2, y = -0.1 * (agent.capacity + 1), width = 0.4, height = (agent.capacity + 1) * 0.2, fill = self.color)
                # When a vehicle is clicked, print some data about it to the console.
                add_event_listener("click", lambda _: self.print_vehicle_info(agent))

    def print_vehicle_info(self, agent: Vehicle):
        print(f"Vehicle {agent.unique_id} clicked.")
        print(f"position = {agent.pos}")
        print(f"plan = {agent.plan}")
        space = agent.model.space
        print(f"Incoming edges from: {space.roads_from(agent.pos)}")
        print(f"Outgoing edges to: {space.roads_to(agent.pos)}")

    def update(self, agent: Vehicle):
        """
        Updates the position ahd heading of the vehicle by translating and rotating the SVG elements.

        Args:
            model (Vehicle): the agent model which the view is connected to.
        """
        # Update vehicle positions
        (x, y) = agent.pos
        with dom().query(f"#vehicle_{agent.unique_id}") as g:
            rotation = { "N" : 0, "E" : 90, "S" : 180, "W" : 270 }
            g["transform"] = f"translate({x + 0.5}, {y + 0.5}) rotate({rotation[agent.heading]})"

class TransportSystemView:
    """
    Provides a view of the road network.
    """
    def __init__(self, model: TransportSystem):
        """
        Initiates the view of the model, which consists of a map and simulation controls.

        Args:
            model (TransportSystem): the transport system model which the view is connected to.
        """
        # Create UI elements
        with dom().query("#simulation"):
            with svg(id = "map", width = "100%", height = "90vh",
                     style = "border: 0.5px solid black; background: lightgreen;"):
                g(id = "road_network")
                g(id = "vehicles")

    def create_agent_view(self, agent: mesa.Agent) -> AgentView | None:
        """
        Creates the view of an agent.
        It determines what view to use based on the class name of the agent.

        Args:
            agent (mesa.Agent): the agent.

        Returns:
            AgentView: the new agent view, or None if no view is available for that class of agents.
        """
#        if agent.__class__.__name__ == "Vehicle":
        if isinstance(agent, Vehicle):
            return VehicleView(agent)
        else:
            return None

    def update_time(self, t: int):
        """
        Updates the time indicator in the user interface.

        Args:
            t (int): the new time.
        """
        with dom().query("#time") as p:
            p.inner_html(t)

    def update(self, model: TransportSystem):
        """
        Updates the map, clearing any previous graphics.
        When drawing the graphics, the internal scale in the SVG is one cell to one unit.
        The viewBox is set to the entire graph, and the graphics is scaled through SVG element styling.

        Args:
            model (TransportSystem): the transport system model to be reflected in the user interface.
        """
        space = model.space
        with dom().query("#map") as m:
            m["viewBox"] = f"0 0 {model.width * 4} {model.height * 4}"
        with dom().query("#road_network", clear = True):
            # Visualize roads
            for (x1, y1), (x2, y2) in space.road_edges():
                line(x1 = x1 + 0.5, y1 = y1 + 0.5, x2 = x2 + 0.5, y2 = y2 + 0.5, 
                     stroke = "lightslategray", stroke_width = 0.8, stroke_linecap = "round")
            # Visualize destinations
            for node in space.road_nodes():                
                (x, y) = node
                if space.is_destination(node):
                    circle(cx =  x + 0.5, cy = y + 0.5, r = 0.25, fill = "darkgray")
        dom().query("#vehicles", clear = True)
        # Add agent views
        for agent in model.schedule.agents:
            agent.view = self.create_agent_view(agent)

class MenuBar:
    """
    Main menu bar of the SoSSim user interface.
    """
    def __init__(self):
        with dom().query("#menubar"):
            with ul():
                li("File")
                li("View")
                li("About")

class UserInteface:
    """
    Creates the user interface of the SoSSim interactive mode.
    """
    def __init__(self, model: TransportSystem, configuration: Configuration):
        # Remove load message and set cursor to default
        with dom().query("#load_msg") as e:
            e.remove()
        with dom().query("body") as b:
            b["style"] = "cursor: default;"
        # Setup main layout
        with dom().query("body"):
            # TODO: Pico CSS navbar does not render as expected.
#            with header():
#                with nav(id = "menubar", cls = "container-fluid"): 
#                    MenuBar()
            with main(cls = "container"):
                with div(id = "main_grid", style = "display: grid; grid-template-columns: 2fr 1fr;"):
                    with div(id = "simulation"):
                        div(id = "controls")
                        SimulationController(model)
                    with div(id = "configuration"):
                        ConfigurationController(model, configuration)
        model.add_view(TransportSystemView(model))