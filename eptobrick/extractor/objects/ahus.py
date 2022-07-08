from . import eplusbindings as epb
from ..utils import utils as ut

m = ut.Nuncius(debug=3)

def untangleAirLoopZones(idf):
    zoneequipment = []
    for zone in idf.ZoneHVAC_EquipmentConnections:
        inlets = []
        outlets = []
        for nodelist in idf.NodeList:
            if nodelist.name == zone.zone_air_inlet_node_or_nodelist_name:
                inlets.extend(ut.getListComponents(nodelist, 'node', 'name'))
            elif nodelist.name == zone.zone_return_air_node_or_nodelist_name or nodelist.name == zone.zone_air_exhaust_node_or_nodelist_name:
                outlets.extend(ut.getListComponents(nodelist, 'node', 'name'))
        # If the 'node or nodelist' did not refer to a nodelist, it means it is a single node.
        if inlets == []:
            inlets.append(zone.zone_air_inlet_node_or_nodelist_name)
        if outlets == []:
            if zone.zone_return_air_node_or_nodelist_name is not None:
                outlets.append(zone.zone_return_air_node_or_nodelist_name)
            if zone.zone_air_exhaust_node_or_nodelist_name is not None:
                outlets.append(zone.zone_air_exhaust_node_or_nodelist_name)
        curzone = [epb.ThermalZone(zone, ut.getEPType(zone), inlets, outlets).create()]
        adus = ut.getListComponents(zone.zone_conditioning_equipment_list_name, 'zone_equipment', 'name')
        for adu in adus:
            terminalunit = adu.air_terminal_name
            curzone.append(epb.AHUComponent(terminalunit, ut.getEPType(terminalunit)).create())
        m.printMessage(f'Extracted zone and ADU nodes for {zone.zone_name.name}', lvl='debug')
        m.printMessage(f'\t{zone.zone_name.name} outlets: {curzone[0].air_outlets}', lvl='debug')
        m.printMessage(f'\t{terminalunit.name} inlets: {curzone[-1].air_inlets}', lvl='debug')


    
    return zoneequipment

def untangleAirLoopSupply(idfahu, idf):
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
    branches = ut.getListComponents(idfahu.branch_list_name, 'branch', 'name')
    components = []
    filtered = []
    for branch in branches:
        components.append(ut.getListComponents(branch, 'component', 'name'))
        for componentlist in components:
            for component in componentlist:
                edgecases = componentEdgeCases(component)
                if edgecases is not None:
                    filtered.extend(edgecases)
                else:
                    filtered.append(epb.AHUComponent(component, ut.getEPType(component)).create())
                ### This is where we check for component type! There is no further nesting.
    
    m.printMessage(f'Extracted supply branch for {idfahu.name}:', lvl='debug')
    m.printMessage(f'\tObjects: {[comp.type for comp in filtered]}', lvl='debug')
    m.printMessage(f'\tSupply inlets: {filtered[0].air_inlets}', lvl='debug')
    m.printMessage(f'\tSupply outlets: {filtered[-1].air_outlets}', lvl='debug')

    ## DEMAND ##

    for supplypath in idf.AirLoopHVAC_SupplyPath:
        if supplypath.supply_air_path_inlet_node_name == demand_inlet:
            splitters = ut.getListComponents(supplypath, 'component', 'name')
            for splitter in splitters:
                filtered.append(epb.AHUComponent(splitter, ut.getEPType(splitter)).create())

    m.printMessage(f'Extracted supply path for {idfahu.name}', lvl='debug')
    m.printMessage(f'\tSupply path starts at: {filtered[-1].air_inlets}', lvl='debug')
    m.printMessage(f'\tSupply path ends at: {filtered[-1].air_outlets}', lvl='debug')
            
    for returnpath in idf.AirLoopHVAC_ReturnPath:

        if returnpath.return_air_path_outlet_node_name == demand_outlet:
            mixers = ut.getListComponents(returnpath, 'component', 'name')
            for mixer in mixers:
                filtered.append(epb.AHUComponent(mixer, ut.getEPType(mixer)).create())

    m.printMessage(f'Extracted return path for {idfahu.name}', lvl='debug')
    m.printMessage(f'\tReturn path starts at: {filtered[-1].air_inlets}', lvl='debug')
    m.printMessage(f'\tReturn path ends at: {filtered[-1].air_outlets}', lvl='debug')

    return filtered, conns

def componentEdgeCases(idfobj):
    filtered = []
    gettype = ut.getEPType(idfobj).split(':')
    if ut.getEPType(idfobj) == 'AirLoopHVAC:OutdoorAirSystem':
        oacomponents = ut.getListComponents(idfobj.outdoor_air_equipment_list_name, 'component', 'name')
        for oacomponent in oacomponents:
            filtered.append(epb.AHUComponent(oacomponent, ut.getEPType(oacomponent)).create())
        return filtered
    elif ut.getEPType(idfobj).split(':')[1] == 'UnitaryHeatPump':
        hpcomponents = [
            idfobj.supply_air_fan_name,
            idfobj.heating_coil_name,
            idfobj.cooling_coil_name,
            idfobj.supplemental_heating_coil_name
        ]
        for hpcomponent in hpcomponents:
            filtered.append(epb.AHUComponent(hpcomponent, ut.getEPType(hpcomponent)).create())
        return filtered
    else:
        return None 

######## DANGER ZONE ######
class FluidConnectionMap():

    def __init__(self) -> None:
        self.map = {}

    def add_point(self, inlet, outlet, name):
        if name not in self.map.keys():
            self.map[name] = {'in' : [], 'out' : [], 'isFedBy' : None, 'feeds' : None}
        self.map[name]['in'].append(inlet)
        self.map[name]['out'].append(outlet)

    def findConnections(self, start, how='feeds'):
        connections = []
        if self.map[start][how] is None:
            for key in self.map.keys():
                if how == 'downstream':
                    if any(self.map[key]['in']) in self.map[start]['out']:
                        connections.append(key)
                else:
                    if any(self.map[key]['out']) in self.map[start]['in']:
                        connections.append(key)
            self.map[start][how] = connections
        else:
            connections.extend(self.map[start][how])
        return connections
        



def findAirLoops(self, idf):
    '''
    Find all HVAC airloops in an IDF
    Parameters:
    idf
        opyplus IDF object
    Returns:
    list
        List of opyplus IDF Records
    '''
    return [airloop for airloop in idf.AirLoopHVAC]

def findBranchComponents(branch, type):
    '''
    Find branch components, depending from system type
    Parameters:
    branch:
        opyplus Record
    type (str):
        Branch type as defined in EnergyPlus
    Returns:
    list:
        List of opyplus records
    '''
    if type == 'AirLoopHVAC:OutdoorAirSystem':
        oas = findOAS(branch)
    elif type == '':
        'Complete all fields'