import platform, os
import attrs
import opyplus as op

from .objects import ahus
import brickschema
from brickschema.namespaces import BRICK
from rdflib import Namespace, RDFS, RDF, URIRef, Graph
from .objects import ahus, sensors
from .utils import utils as ut

m = ut.Nuncius(debug = 1)

class Extractor():

    def __init__(self, verbose=3) -> None:
        m.debug = verbose
        self.graph = Graph()
        self.BRICK = Namespace('https://brickschema.org/schema/1.0.1/Brick#')
        self.BF = Namespace('https://brickschema.org/schema/1.0.1/BrickFrame#')
        self.graph.bind('brick', self.BRICK)
        self.graph.bind('bf', self.BF)
        self.graph.bind('rdfs', RDFS)
        self.graph.bind('rdf', RDF)

    def load(self, eppath):
        '''
        Load an IDF file.

        Parameters:
        eppath : str
            Path to the IDF
        Returns:
        idf
            The eppy.IDF instance of the EnergyPlus model
        '''
        opidf = op.Epm()
        opm = opidf.load(eppath)
        m.printMessage(f'Loaded file: {eppath}')
        return opm


    def bindBuilding(self, idf):
        self.BUILDING = Namespace('http://change.me#')
        self.bldg = idf.Building[0].name.lower().replace(' ', '')
        self.graph.bind(self.bldg, self.BUILDING)
        return self.graph

    def bindAHUs(self, zones, airloop, sdconn, ahuname):
        buffer = []
        airloop = ahus.joinSupplyDemand(airloop, zones)
        airloop = ahus.bypassElements(airloop, sdconn)
        for element in airloop:
            self.graph.add((self.BUILDING[element.name], RDF['type'], self.BRICK[element.btype]))
        for first_element in airloop:
            if first_element.btype != 'HVAC_Zone':
                self.graph.add((self.BUILDING[ahuname], self.BF['hasPart'], self.BUILDING[first_element.name]))
            for second_element in airloop:
                if any(item in first_element.air_outlets for item in second_element.air_inlets):
                    self.graph.add((self.BUILDING[first_element.name], self.BF['feeds'], self.BUILDING[second_element.name]))
                if any(item in second_element.air_outlets for item in first_element.air_inlets):
                    self.graph.add((self.BUILDING[second_element.name], self.BF['feeds'], self.BUILDING[first_element.name]))

            # Here, check inlets and outlets and define relationship.
        return airloop
        

    def createAHUs(self, idf):
        # for ahu in ahus untangle
        m.printMessage(f'Extracting air handling units...')
        zones = ahus.untangleAirLoopZones(idf)
        ahus_stitched = []
        for ahu in idf.AirLoopHVAC:
            m.printMessage(f'Parsing {ahu.name}...', lvl='debug')
            self.graph.add((self.BUILDING[ahu.name], RDF['type'], self.BRICK['AHU']))
            airloop, sdconn = ahus.untangleAirLoopSupply(ahu, idf)
            sensor_bindings = sensors.parseSensors(idf, airloop)
            ahus_stitched.append(self.bindAHUs(zones, airloop, sdconn, ahu.name))
        outname = idf.Building[0].name.lower().replace(' ', '')
        self.graph.serialize(destination=f'{outname}.ttl', format='turtle')
        return self.graph