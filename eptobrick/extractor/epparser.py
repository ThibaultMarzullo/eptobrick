import platform, os
import attrs
import opyplus as op

#from .objects import ahus
import brickschema
from brickschema.namespaces import BRICK
from rdflib import Namespace, RDFS, RDF, URIRef, Graph
#from .objects import ahus, sensors
from .utils import utils as ut

m = ut.Nuncius(debug = 1)

class Extractor():

    def __init__(self, verbose=3) -> None:
        m.debug = verbose
        self.graph = Graph()
        self.BRICK = Namespace('https://brickschema.org/schema/Brick#') #1.0.1 is not supported anymore
        self.BF = Namespace('https://brickschema.org/schema/Brick#') #BrickFrame -> BRICK
        self.graph.bind('brick', self.BRICK)
        #self.graph.bind('bf', self.BF)
        self.graph.bind('rdfs', RDFS)
        self.graph.bind('rdf', RDF)

    def load(self, eppath):
        '''
        Load an IDF file.

        Args:
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


    def walkElements(self, opm):

        for category in opm:
            for element in category:
                pass

    def saveGraph(self):
        self.graph.serialize(destination=f'{self.bldgname}.ttl', format='turtle')
        return self.graph