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
            airloop = self.untangleAirLoop(ahu, idf)

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

    def untangleAirLoopZones(self, idf):
        zoneequipment = []
        for zone in idf.ZoneHVAC_EquipmentConnections:
            inlets = []
            outlets = []
            for nodelist in idf.NodeList:
                if nodelist.name == zone.zone_air_inlet_node_or_nodelist_name:
                    inlets.extend(self.getListComponents(nodelist, 'node', 'name'))
                elif nodelist.name == zone.zone_return_air_node_or_nodelist_name or nodelist.name == zone.zone_air_exhaust_node_or_nodelist_name:
                    outlets.extend(self.getListComponents(nodelist, 'node', 'name'))
            # If the 'node or nodelist' did not refer to a nodelist, it means it is a single node.
            if inlets == []:
                inlets.append(zone.zone_air_inlet_node_or_nodelist_name)
            if outlets == []:
                if zone.zone_return_air_node_or_nodelist_name is not None:
                    outlets.append(zone.zone_return_air_node_or_nodelist_name)
                if zone.zone_air_exhaust_node_or_nodelist_name is not None:
                    outlets.append(zone.zone_air_exhaust_node_or_nodelist_name)
            curzone = [ahus.ThermalZone(zone, self.getEPType(zone), inlets, outlets).create()]
            adus = self.getListComponents(zone.zone_conditioning_equipment_list_name, 'zone_equipment', 'name')
            for adu in adus:
                terminalunit = adu.air_terminal_name
                curzone.append(ahus.AHUComponent(terminalunit, self.getEPType(terminalunit)).create())
            # search Core_ZN Direct Air ADU in IDF
            self.printMessage(f'Extracted zone and ADU nodes for {zone.zone_name.name}', lvl='debug')

            self.printMessage(f'\t{zone.zone_name.name} outlets: {curzone[0].air_outlets}', lvl='debug')
            self.printMessage(f'\t{terminalunit.name} inlets: {curzone[-1].air_inlets}', lvl='debug')


        
        return zoneequipment

    def untangleAirLoopSupply(self, idfahu, idf):
        supply_inlet = idfahu.supply_side_inlet_node_name
        supply_outlet = idfahu.supply_side_outlet_node_names
        demand_inlet = idfahu.demand_side_inlet_node_names
        demand_outlet = idfahu.demand_side_outlet_node_name

        conns = {
            'sin' : supply_inlet,
            'sout' : supply_outlet,
            'din' : demand_inlet,
            'dout' : demand_outlet
        }

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
        
        self.printMessage(f'Extracted supply branch for {idfahu.name}:\n\tObjects: {[comp.type for comp in filtered]}', lvl='debug')
        self.printMessage(f'\tSupply inlets: {filtered[0].air_inlets}\n\tSupply outlets: {filtered[-1].air_outlets}', lvl='debug')

        ## DEMAND ##

        for supplypath in idf.AirLoopHVAC_SupplyPath:
            if supplypath.supply_air_path_inlet_node_name == demand_inlet:
                splitters = self.getListComponents(supplypath, 'component', 'name')
                for splitter in splitters:
                    filtered.append(ahus.AHUComponent(splitter, self.getEPType(splitter)).create())

        self.printMessage(f'Extracted supply path for {idfahu.name}\n\tSupply path starts at: {filtered[-1].air_inlets}', lvl='debug')
        self.printMessage(f'\tSupply path ends at: {filtered[-1].air_outlets}', lvl='debug')
                
        for returnpath in idf.AirLoopHVAC_ReturnPath:

            if returnpath.return_air_path_outlet_node_name == demand_outlet:
                mixers = self.getListComponents(returnpath, 'component', 'name')
                for mixer in mixers:
                    filtered.append(ahus.AHUComponent(mixer, self.getEPType(mixer)).create())

        self.printMessage(f'Extracted return path for {idfahu.name}\n\tReturn path starts at: {filtered[-1].air_inlets}', lvl='debug')
        self.printMessage(f'\tReturn path ends at: {filtered[-1].air_outlets}', lvl='debug')

        return filtered, conns

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


