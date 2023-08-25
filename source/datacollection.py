"""
Datacollection for the SoSSim system-of-systems simulator.
It defines a subclass of mesa's data collector, that collects data on all defined state variables.
"""
from mesa.datacollection import DataCollector

import core
from dynamics import all_state_variables

class StateDataCollector(DataCollector):

    def __init__(self): 
        """
        Creates a data collector that collects all state variables defined in the system.
        Separate tables are provided for each class that contains state variables.
        Each table has one column for each state variable, and also one column for the agent unique id.
        """
        tables = all_state_variables(core.Entity)
        for cls, vars in tables.items():
            tables[cls] = ["time", "unique_id"] + vars
        super().__init__(tables = tables)

    def collect(self, model: core.Model):
        """
        Collects all data for the given model object at the current time.

        Args:
            model (core.Model): the model for which data is to be collected.
        """
        time = model.schedule.time
        for agent in model.agents():
            table_name = type(agent).__name__
            for var in self.tables[table_name]:
                if var == "time":
                    self.tables[table_name][var].append(time)
                else:
                    self.tables[table_name][var].append(getattr(agent, var))

    def has_rows(self, table_name: str = "") -> bool:
        """
        Returns True if and only if the table with the given name contains any rows.
        If no table name is given, it returns True if any of the table contains a row.

        Args:
            table_name (str): the name of the table.

        Returns:
            bool: True if and only if the table (or any of the table) contains any rows.
        """
        if table_name:
            return self.tables[table_name]["unique_id"] 
        else:
            return any(self.tables[name]["unique_id"] for name in self.tables.keys())