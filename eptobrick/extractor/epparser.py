import platform, os
import attrs
import opyplus as op

from .objects import ahus
import brickschema
from brickschema.namespaces import BRICK
from rdflib import Namespace, RDFS, RDF, URIRef, Graph
from .objects import ahus
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

    def createAHUs(self, idf):
        # for ahu in ahus untangle
        m.printMessage(f'Extracting air handling units...')
        for ahu in idf.AirLoopHVAC:
            m.printMessage(f'Parsing {ahu.name}...', lvl='debug')
            self.graph.add((self.BUILDING[ahu.name], RDF['type'], self.BRICK['AHU']))
            zones = ahus.untangleAirLoopZones(idf)
            airloop = ahus.untangleAirLoopSupply(ahu, idf)

        pass