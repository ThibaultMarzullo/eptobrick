import platform, os, json
import attrs
import opyplus as op

import brickschema
from brickschema.namespaces import BRICK
from rdflib import Namespace, RDFS, RDF, URIRef, Graph
from utils import utils as ut

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

        with open('dictmap.json') as f:
            self.epbindings = json.load(f)

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
        
        allcomponents = []
        for category in opm:
            for element in category:
                allcomponents.extend(self.getComponent(element))
            # try:
            #     for element in category:
            #         allcomponents.extend(self.getComponent(element))
            # except:
            #     m.printMessage(f"Empty category: {category}", lvl='debug')

    def getComponent(self, element):
        res = []
        epcomponent = Component(element)
        if epcomponent.etype in self.epbindings.keys():
            bindings = self.epbindings[epcomponent.etype]
            epcomponent.assignBasics(bindings)
            res.extend([epcomponent])
            for method in bindings["rules"].keys():
                if hasattr(epcomponent, str(method)):
                    mth = getattr(epcomponent, str(method))
                    subcomponents = mth(bindings["rules"][method])
                    if isinstance(subcomponents, list):
                        for subc in subcomponents:
                            try:
                                subc = subc
                                res.extend(self.getComponent(subc))
                            except Exception as e:
                                subc = subc
                                print(e)
                                res.extend([subcomponents])
                                pass

                else:
                    m.printMessage(f"Could not find method: {method}", lvl='debug')
            return res
        else: 
            m.printMessage(f"Category not defined in the EP bindings dict: {epcomponent.etype}", lvl='debug')
            return []

    def saveGraph(self):
        self.graph.serialize(destination=f'{self.bldgname}.ttl', format='turtle')
        return self.graph

class Component():
    def __init__(self, idfelem) -> None:
        self.name = None
        self.idfelem = idfelem
        self.etype = ut.getEPType(idfelem)
        self.btype = None
        self.inlets = []
        self.outlets = []
        self.bpredicates = {}

    def assignBasics(self, bindings):
        self.btype = bindings["BrickType"]
        self.name = self.idfelem.name

    def addInlets(self, inlets):
        #TODO: check for NodeList
        for inlet in inlets:
            self.inlets.append(getattr(self.idfelem, inlet))
    
    def addOutlets(self, outlets):
        #TODO: check for NodeList
        for outlet in outlets:
            self.outlets.append(getattr(self.idfelem, outlet))

    def addPredicate(self, predicate, elements):
        if predicate in self.bpredicates.keys():
            self.bpredicates[predicate].extend([element.name for element in elements])
        else:
            self.bpredicates[predicate] = [element.name for element in elements]

    def unpackList(self, eplist, type_, attr_):
        res = []
        
        for i in range(1, 100):
            if attr_ != "":
                attrstr = f"{type_}_{i}_{attr_}"
            else:
                attrstr = f"{type_}_{i}"
            try:
                if getattr(eplist, attrstr) is not None:
                    res.extend([getattr(eplist, attrstr)])
            except:
                break
        return res

    def getListElements(self, listname):
        return [getattr(self.idfelem, element) for element in listname if getattr(self.idfelem, element) is not None]

    def unpackBranch(self, branchlistnames):
        branchlists = self.getListElements(branchlistnames)
        subcomponents = []
        for branchlist in branchlists:
            branches = self.unpackList(branchlist, 'branch', 'name')
            for branch in branches:
                bsc = self.unpackList(branch, 'component', 'name')
                subcomponents.extend(bsc)
            self.addPredicate("hasPart", subcomponents)
        return subcomponents

    def unpackOAS(self, oaslistsnames):
        oaslists = self.getListElements(oaslistsnames)
        subcomponents = []
        for oaslist in oaslists:
            #TODO add predicate?
            subcomponents.extend(self.unpackList(oaslist, 'component', 'name'))
        return subcomponents

    def addOAS(self, oasnodes):
        #TODO see what to do with nodelists. Maybe these should be explicitly
        # linked to boundary conditions, or something else
        pass

    def genericUnpack(self, unpacklist):
        subcomponents = self.getListElements(unpacklist)
        return subcomponents

    def unpackStorage(self, storagelist):
        # Keep this method separate just in case we encounter edge cases down the line
        return self.genericUnpack(storagelist)

    def unpackReheatSystem(self, reheatlist):
        # Keep this method separate just in case we encounter edge cases down the line
        return self.genericUnpack(reheatlist)
    
    def zoneEquipment(self, equiplist):
        self.zoneequip = self.unpackList(equiplist, 'zone_equipment', 'name')
        
    def manualPredicate(self, params):
        self.addPredicate(params["predicate"], self.getListElements(params["elements"]))

    def dualSetpoint(self, schedules):
        #TODO see how to use the TimeSeriesReference BRICK type
        pass

    def getSetpoint(self, schedules):
        #TODO see how to use the TimeSeriesReference BRICK type
        pass

    def extensibleMethod(self, mdict):
        #TODO: what if there are several method extensions needed?
        for meth in mdict:
            if hasattr(self, meth["method"]):
                mth = getattr(self, meth["method"])
                extendedlist = self.unpackList(self.idfelem, meth["type_"], meth["attr_"])
                for elem in extendedlist:
                    mth(elem)

    # def duplicateElement(self, num, epobj):
    #     if isinstance(num, int):
    #         pass
