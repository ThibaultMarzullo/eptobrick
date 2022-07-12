from . import eplusbindings as epb
from ..utils import utils as ut

m = ut.Nuncius(debug=3)

def bypassElements(airloop, sdconn):

    for element in airloop:
        if element.btype is not None:
            newairloop = [element]
            break
    
    for element in airloop:
        if sdconn['sout'] in element.air_outlets:
            element.air_outlets.append(sdconn['din'])
            element.air_outlets = [item for item in element.air_outlets if item != sdconn['sout']]
        if sdconn['sin'] in element.air_inlets:
            element.air_inlets.append(sdconn['dout'])
            element.air_inlets = [item for item in element.air_inlets if item != sdconn['sin']]

    noNones = [item for item in airloop if item.btype is not None]

    while True:
        for fe in newairloop:
            for se in airloop:
                if any([item in fe.air_outlets for item in se.air_inlets]):
                    if se.btype is not None and se not in newairloop:
                        newairloop.append(se)
                    elif se.btype is None:
                        jump = [item for item in fe.air_outlets if item not in se.air_inlets]
                        if jump == []:
                            fe.air_outlets = se.air_outlets
                        else:
                            fe.air_outlets = jump.append(se.air_outlets) ## ICI##
        if all([item in newairloop for item in noNones]):
            return newairloop


def joinSupplyDemand(airloop, zones):
    for zone in zones:
        for ze in zone:
            for ae in airloop:
                if any([item in ae.air_inlets for item in ze.air_outlets]) or any([item in ze.air_inlets for item in ae.air_outlets]):
                    airloop.extend(zone)
                    return airloop

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
            if ut.getEPType(adu) == 'ZoneHVAC:AirDistributionUnit':
                terminalunit = adu.air_terminal_name
                edgecase = componentEdgeCases(terminalunit)
                if edgecase is not None:
                    curzone.extend(edgecase)
                else:
                    curzone.append(epb.AHUComponent(terminalunit, ut.getEPType(terminalunit)).create())
            else:
                curzone.append(epb.AHUComponent(adu, ut.getEPType(adu)).create())
        zoneequipment.append(curzone)
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
                edgecases = componentEdgeCases(splitter)
                if edgecases is None:
                    filtered.append(epb.AHUComponent(splitter, ut.getEPType(splitter)).create())
                else:
                    filtered.extend(edgecases)

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
    elif gettype[1] == 'UnitaryHeatPump':
        hpcomponents = [
            idfobj.supply_air_fan_name,
            idfobj.heating_coil_name,
            idfobj.cooling_coil_name,
            idfobj.supplemental_heating_coil_name
        ]
        for hpcomponent in hpcomponents:
            filtered.append(epb.AHUComponent(hpcomponent, ut.getEPType(hpcomponent)).create())
    elif gettype[0] == 'CoilSystem':
        coilcomponents = idfobj.cooling_coil_name
        filtered.append(epb.AHUComponent(coilcomponents, ut.getEPType(coilcomponents)).create())
    elif gettype[0] == 'AirLoopHVAC' and gettype[1] == 'ZoneSplitter':
        filtered.append(epb.AHUComponent(idfobj, ut.getEPType(idfobj)).create())
    elif gettype[0] == 'AirTerminal':
        if gettype[3] == 'Reheat':
            filtered.append(epb.AHUComponent(idfobj.reheat_coil_name, ut.getEPType(idfobj.reheat_coil_name)).create())
            filtered.append(epb.AHUComponent(idfobj, ut.getEPType(idfobj)).create())

    if filtered == []:
        return None 
    else:
        return filtered