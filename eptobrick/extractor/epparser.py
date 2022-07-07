import platform, os
import attrs
import opyplus as op
from .objects import ahus
import brickschema
from brickschema.namespaces import BRICK
from rdflib import Namespace, RDFS, RDF, URIRef, Graph
from .objects import ahus
from termcolor import colored

class Extractor():

    def __init__(self, verbose=3) -> None:
        self.debug = verbose
        self.graph = Graph()
        self.BRICK = Namespace('https://brickschema.org/schema/1.0.1/Brick#')
        self.BF = Namespace('https://brickschema.org/schema/1.0.1/BrickFrame#')
        self.graph.bind('brick', self.BRICK)
        self.graph.bind('bf', self.BF)
        self.graph.bind('rdfs', RDFS)
        self.graph.bind('rdf', RDF)

    def printMessage(self, message, lvl='info'):
        if lvl == 'info':
            print(colored(message, 'blue'))
        elif self.debug > 2:
            print(colored(f'Debug:\t{message}', 'yellow'))
        

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
        self.printMessage(f'Loaded file: {eppath}')
        return opm

    def getEPType(self, inp):
        return inp._table._dev_descriptor.table_name

    def bindBuilding(self, idf):
        self.BUILDING = Namespace('http://change.me#')
        self.bldg = idf.Building.name.lower().replace(' ', '')
        self.graph.bind(self.bldg, self.BUILDING)

    def createAHUs(self, idf):
        # for ahu in ahus untangle
        self.printMessage(f'Extracting air handling units...')
        for ahu in idf.AirLoopHVAC:
            self.printMessage(f'{ahu.name}', lvl='debug')
            self.graph.add(self.BUILDING[ahu.name], RDF['type'], self.BRICK['AHU'])
            airloop = self.untangleAirLoop(ahu)

        pass
    
    def getListComponents(self, idflist, type, value):
        components = []
        i = 1
        while True:
            try:
                components.append(getattr(idflist, f'{type}_{i}_{value}'))
                i += 1
            except:
                break
        return list(filter(None, components)) #sometimes we end up with trailing 'None' values

    def untangleAirLoop(self, idfahu):
        supply_inlet = idfahu.supply_side_inlet_node_name
        supply_outlet = idfahu.supply_side_outlet_node_names
        demand_inlet = idfahu.demand_side_inlet_node_names
        demand_outlet = idfahu.demand_side_outlet_node_name

        ## SUPPLY ##
        branches = self.getListComponents(idfahu.branch_list_name, 'branch', 'name')
        components = []
        filtered = []
        for branch in branches:
            components.append(self.getListComponents(branch, 'component', 'name'))
            for componentlist in components:
                for component in componentlist:
                    edgecases = self.componentEdgeCases(component)
                    if edgecases is not None:
                        filtered.extend(edgecases)
                    else:
                        filtered.append(ahus.AHUComponent(component, self.getEPType(component)).create())
                    ### This is where we check for component type! There is no further nesting.
        
        self.printMessage('Extracted supply branch containing the following objects:', lvl='debug')
        self.printMessage(f'\tObjects: {[comp.type for comp in filtered]}', lvl='debug')
        self.printMessage(f'\tSupply inlets: {filtered[0].air_inlets}', lvl='debug')
        self.printMessage(f'\tSupply outlets: {filtered[-1].air_outlets}', lvl='debug')

        ## DEMAND ##

        

        #demand inlet = supply outlet / demand outlet = supply inlet

        # untangle demand side
            # this is where the mixers, splitters, terminal units and zones will be
            # dig into nested lists until we arrive to the equipment

        # if necessary, fix the supply -> demand and demand -> supply joining nodes, so that the equipment inlet/outlets point to those of the
        # next equipment in line

    def componentEdgeCases(self, idfobj):
        filtered = []
        gettype = self.getEPType(idfobj).split(':')
        if self.getEPType(idfobj) == 'AirLoopHVAC:OutdoorAirSystem':
            oacomponents = self.getListComponents(idfobj.outdoor_air_equipment_list_name, 'component', 'name')
            for oacomponent in oacomponents:
                filtered.append(ahus.AHUComponent(oacomponent, self.getEPType(oacomponent)).create())
            return filtered
        elif self.getEPType(idfobj).split(':')[1] == 'UnitaryHeatPump':
            hpcomponents = [
                idfobj.supply_air_fan_name,
                idfobj.heating_coil_name,
                idfobj.cooling_coil_name,
                idfobj.supplemental_heating_coil_name
            ]
            for hpcomponent in hpcomponents:
                filtered.append(ahus.AHUComponent(hpcomponent, self.getEPType(hpcomponent)).create())
            return filtered
        else:
            return None 


    def walkAirLoop(self, airloop_in):
        branch_lists = airloop_in.branch_list_name
        branches = []
        systems = []
        for i in range(1, 100):
            if hasattr(branch_lists, f"component_{i}_name"):
                branches.append(branch_lists[f"branch_{i}_name"])
            else:
                if self.debug > 2:
                    print("No more branches to explore")
                break
        for branch in branches:
            for i in range(1, 100):
                if hasattr(branch, f"component_{i}_name"):
                    components = self.getSystemsInBranch(
                        branch[f"component_{i}_name"], 
                        branch[f"component_{i}_object_type"], 
                        branch[f"component_{i}_inlet_node_name"], 
                        branch[f"component_{i}_outlet_node_name"]
                        )
                    systems.append(components)
                else:
                    break
        return branches

    def getSystemsInBranch(self, airloop, type, inlet, outlet):

        # this should start populating the BRICK model instead of recording architectures.

        systems = {
            'inlet' : inlet,
            'outlet' : outlet,
            'type' : getBRICKType(type),
            'elements' : []
        }
        systems['elements'] = getElementsByType()
        return None
