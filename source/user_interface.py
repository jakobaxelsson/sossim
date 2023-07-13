"""
User interface for the SoSSim system-of-systems simulator.
The user interface is based on the Model-View-Controller pattern.
The model is a Mesa model, and this module provides simulation controller and user interface elements.
The user interface is provided as HTML DOM elements which is manipulated using the domscript module.
"""

import random

import mesa

from domscript import *

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
    def __init__(self, model):
        """
        Sets up the configuration controller, adding the necessary DOM elements.
        """
        self.model = model
        with dom().query("#configuration"):
            with div(id = "model_controls", cls = "flex demo"):
                with label("#Agents:"):
                    self.N = input_(id = "nb_agents")
                with label("Width:"):
                    self.width = input_(id = "grid_width")
                with label("Height:"):
                    self.height = input_(id = "grid_height")
                with label("Destination density:"):
                    self.destination_density = input_(id = "destination_density")
                with label("Seed:"):
                    self.random_seed = input_(id = "random_seed", value = self.model.random_seed)
                with button("Generate", cls = "error"):
                    add_event_listener("click", lambda _: self.generate())

    def generate(self):
        """
        Generates a new model based on parameter values in the input fields in the simulation controls.
        """
        args = dict()
        if self.N.dom_element.value:
            args["N"] = int(self.N.dom_element.value)
        if self.width.dom_element.value:
            args["width"] = int(self.width.dom_element.value)
        if self.height.dom_element.value:
            args["height"] = int(self.height.dom_element.value)
        if self.destination_density.dom_element.value:
            args["destination_density"] = float(self.destination_density.dom_element.value)
        if self.random_seed.dom_element.value:
            args["random_seed"] = int(self.random_seed.dom_element.value)
        self.model.generate(**args)
        self.random_seed.dom_element.value = self.model.random_seed

class AgentView: 
    """
    A common superclass for agent views.
    """
    pass

class VehicleView(AgentView):
    """
    Renders a vehicle on the map.
    """
    def __init__(self, model: mesa.Agent):
        """
        Draws the vehicle in its initial position.
        The size of the vehicle reflects its load capacity.
        The rotation reflects its heading.
        It is assigned a random color, to makes it easier to follow a specific vehicle on the screen.

        Args:
            model (mesa.Agent): the agent model which the view is connected to.
        """
        # Draw the vehicle
        self.color = "#" + "".join([random.choice(list("0123456789abcdef")) for x in range(6)])
        (x, y) = model.pos
        with dom().query("#vehicles"):
            rotation = { "N" : 0, "E" : 90, "S" : 180, "W" : 270 }
            with g(id = f"vehicle_{model.unique_id}", transform = f"translate({x + 0.5}, {y + 0.5}) rotate({rotation[model.heading]})"): 
                rect(x = -0.2, y = -0.1 * (model.capacity + 1), width = 0.4, height = (model.capacity + 1) * 0.2, fill = self.color)
                # When a vehicle is clicked, print some data about it to the console.
                add_event_listener("click", lambda _: self.print_vehicle_info(model))

    def print_vehicle_info(self, model):
        print(f"Vehicle {model.unique_id} clicked.")
        print(f"position = {model.pos}")
        print(f"plan = {model.plan}")
        rnw = model.model.space.road_network
        print(f"Incoming edges from: {[n for (n, _) in rnw.in_edges(model.pos)]}")
        print(f"Outgoing edges to: {[n for (_, n) in rnw.out_edges(model.pos)]}")

    def update(self, model: mesa.Agent):
        """
        Updates the position ahd heading of the vehicle by translating and rotating the SVG elements.

        Args:
            model (mesa.Agent): the agent model which the view is connected to.
        """
        # Update vehicle positions
        (x, y) = model.pos
        with dom().query(f"#vehicle_{model.unique_id}") as g:
            rotation = { "N" : 0, "E" : 90, "S" : 180, "W" : 270 }
            g["transform"] = f"translate({x + 0.5}, {y + 0.5}) rotate({rotation[model.heading]})"

class TransportSystemView:
    """
    Provides a view of the road network.
    """
    def __init__(self, model: mesa.Model):
        """
        Initiates the view of the model, which consists of a map and simulation controls.

        Args:
            model (mesa.Agent): the agent model which the view is connected to.
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
        if agent.__class__.__name__ == "Vehicle":
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

    def update(self, model: mesa.Model):
        """
        Updates the map, clearing any previous graphics.
        When drawing the graphics, the internal scale in the SVG is one cell to one unit.
        The viewBox is set to the entire graph, and the graphics is scaled through SVG element styling.

        Args:
            model (mesa.Model): the model to be reflected in the user interface.
        """
        rnw = model.space.road_network
        with dom().query("#map") as m:
            m["viewBox"] = f"0 0 {model.width * 4} {model.height * 4}"
        with dom().query("#road_network", clear = True):
            # Visualize roads
            for ((x1, y1), (x2, y2)) in rnw.edges():
                line(x1 = x1 + 0.5, y1 = y1 + 0.5, x2 = x2 + 0.5, y2 = y2 + 0.5, 
                     stroke = "lightslategray", stroke_width = 0.8, stroke_linecap = "round")
            # Visualize destinations
            for (x, y) in rnw.nodes():                
                if rnw.nodes[(x, y)]["destination"]:
                    circle(cx =  x + 0.5, cy = y + 0.5, r = 0.25, fill = "darkgray")
        dom().query("#vehicles", clear = True)

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
    def __init__(self, model: mesa.Model):
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
                        ConfigurationController(model)