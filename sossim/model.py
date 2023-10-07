"""
Provides models for the SoSSim system-of-systems simulator.

Partial UML class diagram:

```mermaid
classDiagram
    `core.Model` <|-- TransportSystem
    TransportSystem: step()
    TransportSystem: manifest()
    TransportSystem: to_archive_content(...)
```
"""
from datetime import datetime
import io
import json
import random
import sys
from typing import Annotated, Any
import zipfile

from sossim.configuration import Configuration, configurable
import sossim.core as core
from sossim.datacollection import StateDataCollector
from sossim.entities import Cargo, Vehicle
import sossim.space as space

@configurable
class TransportSystem(core.Model):
    # Define configuration parameters relevant to this class
    num_vehicles: Annotated[int, "Param", "number of vehicles"] = 10
    num_cargos:   Annotated[int, "Param", "number of cargos"] = 10
    random_seed:  Annotated[int, "Param", "seed for random number generator (use -1 to initialize from system time)"] = -1
    collect_data: Annotated[bool, "Param", "enable data collection of state variables"] = True

    def __init__(self, configuration: Configuration):
        """
        Creates a transport system model.

        Args:
            configuration (Configuration): the configuration of parameters from which the model is generated.
        """
        self.generation_start_time = datetime.utcnow()

        # Initialize superclass and configuration
        super().__init__()
        self.configuration = configuration
        configuration.initialize(self)
        
        # Setup random number generation.
        if self.random_seed == -1:
            self.random_seed = random.randrange(sys.maxsize)
        self.random.seed(self.random_seed)

        # Create the space
        self.space = space.RoadNetworkGrid(configuration, self)

        # Create vehicles
        for i in range(self.num_vehicles):
            Vehicle(self, configuration)

        # Create cargos
        for i in range(self.num_cargos):
            Cargo(self, configuration)
    
        # Setup data collection
        if self.collect_data:
            self.data_collector = StateDataCollector()
            self.data_collector.collect(self)
        else:
            self.data_collector = None

        self.generation_end_time = datetime.utcnow()

    def step(self):
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        self.update_views()
        if self.data_collector:
            self.data_collector.collect(self)

    def manifest(self) -> dict[str, Any]:
        """
        Returns various information about the model as a dict structure.

        Returns:
            dict[str, Any]: the manifest as a dict.
        """
        result: dict[str, Any] = dict()
        # TODO: Add more information about the model here
        result["files"] = dict()
        result["generation_start_time"] = str(self.generation_start_time)
        result["generation_end_time"] = str(self.generation_end_time)
        return result

    def to_archive_content(self, *extras: tuple[str, str, str]) -> dict[str, str]:
        """
        Returns the information in this model as an archive.
        The structure of the archive is a dict whose items are file names and file content.
        This can then easily be mapped to e.g. a zip archive.
        The contents of the archive is a json-formatted file of the configuration.
        If data collection was enabled, it also contains the collected data.
        This is represented as one csv-formatted file for each table in the data collection, where the file name is the name of the table.
        The archive also contains a manifest.json file, with various meta-information about the contents.
        If extra arguments are provided, these should be tuples of three strings: file name, file content, and file description.

        Arguments:
            extras: tuple[str, str, str]: additional iterms to be added.

        Returns:
            dict[str, str]: the archive file names and content.
        """
        archive = dict()

        # Create the manifest information and extend it with information about files.
        manifest = self.manifest()
        manifest["save_time"] = str(datetime.utcnow())
        manifest["files"]["manifest.json"] = "Meta-information about the content of this file archive"

        # Create configuration file
        archive["configuration.json"] = self.configuration.to_json()
        manifest["files"]["configuration.json"] = "The configuration used to create the model"

        # Create data files
        if dc := self.data_collector:
            for table_name in dc.tables.keys():
                if dc.has_rows(table_name):
                    archive[table_name + ".csv"] =  dc.get_table_dataframe(table_name).to_csv()
                    manifest["files"][table_name + ".csv"] = f"Data collected for the agent class {table_name}"

        # Add extra files
        for file_name, file_content, file_description in extras:
            archive[file_name] =  file_content
            manifest["files"][file_name] = file_description

        # Add the manifest file
        archive["manifest.json"] = json.dumps(manifest, indent = 4)

        return archive