import random

from domscript import *

class SimulationController:

    def __init__(self, model):
        self.model = model
        self.timer = None
        with dom().query("#controls"):
            with div(id = "model_controls", cls = "flex demo"):
                with label("#Agents:"):
                    self.N = input_(id = "nb_agents")
                with label("Width:"):
                    self.width = input_(id = "grid_width")
                with label("Height:"):
                    self.height = input_(id = "grid_height")
                with label("Seed:"):
                    self.random_seed = input_(id = "random_seed", value = self.model.random_seed)
                with button("Generate", cls = "error"):
                    add_event_listener("click", lambda _: self.generate())
            with div(id = "simulation_controls"):
                with button("Step"):
                    add_event_listener("click", lambda _: self.model.step())
                with button("Run"):
                    add_event_listener("click", lambda _: self.run())
                with button("Stop"):
                    add_event_listener("click", lambda _: self.stop())
                span("Time: ")
                span("0", id = "time")

    def generate(self):
        args = dict()
        if self.N.dom_element.value:
            args["N"] = int(self.N.dom_element.value)
        if self.width.dom_element.value:
            args["width"] = int(self.width.dom_element.value)
        if self.height.dom_element.value:
            args["height"] = int(self.height.dom_element.value)
        if self.random_seed.dom_element.value:
            args["random_seed"] = int(self.random_seed.dom_element.value)
        self.model.generate(**args)
        self.random_seed.dom_element.value = self.model.random_seed
        
    def run(self):
        # Runs the simulation by repeatedly invoking step (with a small delay between steps).
        self.timer = js.setInterval(create_proxy(self.model.step), 250)

    def stop(self):
        # Stops a running simulation.
        if self.timer:
            js.clearInterval(self.timer)

class VehicleView:

    def __init__(self, model, cell_size):
        # Draw the vehicle
        self.cell_size = cs = cell_size
        self.color = "#" + "".join([random.choice(list("0123456789abcdef")) for x in range(6)])
        (x, y) = model.pos
        with dom().query("#vehicles"):
            rotation = { "N" : 0, "E" : 90, "S" : 180, "W" : 270 }
            with g(id = f"vehicle_{model.unique_id}", transform = f"translate({x * cs + cs / 2}, {y * cs + cs / 2}) rotate({rotation[model.heading]})"): 
                x = -cs * 0.2
                # If c = 2, y = 0.3; c = 3, y = 0.2; c = 4, y = 0.1
                y = -cs * (model.capacity + 1) * 0.1
                h = (model.capacity + 1) * cs * 0.2
                w = cs * 0.4
                rect(x = x, y = y, width = w, height = h, fill = self.color)

    def update(self, model):
        # Update vehicle positions
        cs = self.cell_size
        (x, y) = model.pos
        with dom().query(f"#vehicle_{model.unique_id}") as g:
            rotation = { "N" : 0, "E" : 90, "S" : 180, "W" : 270 }
            g["transform"] = f"translate({x * cs + cs / 2}, {y * cs + cs / 2}) rotate({rotation[model.heading]})"

class TransportSystemView:

    def __init__(self):
        # Remove load message and set cursor to default
        with dom().query("#load_msg") as e:
            e.remove()
        with dom() as b:
            b["style"] = "cursor: default;"
        # Create UI elements
        self.width = 800
        self.height = 800

        with dom().query("#content"):
            div(id = "controls")
            with svg(id = "map", width = self.width, height = self.height, style = "border: 0.5px solid black;"):
                rect(id = "map_background", x = 0, y = 0, width = self.width, height = self.height, fill = "lightgreen")
                g(id = "road_network")
                g(id = "vehicles")

    def create_agent_view(self, agent):
        if agent.__class__.__name__ == "Vehicle":
            return VehicleView(agent, self.cell_size)

    def update_time(self, t):
        # Update time
        with dom().query("#time") as p:
            p.inner_html(t)

    def update(self, model):
        # Draw grid world, clearing any previous graphics
        self.cell_size = cs = min(self.width // model.width, self.height // model.height) / 4
        rnw = model.grid.road_network
        with dom().query("#map_background") as m:
            m["width"] = self.cell_size * model.width * 4
            m["height"] = self.cell_size * model.height * 4
        with dom().query("#road_network", clear = True):
            for ((x1, y1), (x2, y2)) in rnw.edges():
                line(x1 = x1 * cs + cs/2, 
                     y1 = y1 * cs + cs/2, 
                     x2 = x2 * cs + cs/2, 
                     y2 = y2 * cs + cs/2, 
                     stroke = "lightslategray", stroke_width = cs * 0.8, stroke_linecap = "round")
                # Visualize destinations                
                if rnw.nodes[(x1, y1)]["destination"]:
                    circle(cx =  x1 * cs + cs/2, cy = y1 * cs + cs/2, r = cs/4, fill = "darkgray")
        dom().query("#vehicles", clear = True)