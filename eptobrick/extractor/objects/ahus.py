class AHU():
    pass
class AHUComponent():

    def __init__(self, idfobj, objtype) -> None:
        
        #define base properties here
        self.idfElement = idfobj
        self.name = idfobj.name
        self.type = objtype
        self.air_inlets = None
        self.air_outlets = None
        self.data = {}
        self.btype = None

    def add_property(self, property, values):
        self.data[property] = values

    def add_inlet(self, name):
        self.add_airconn('air_inlets', name)

    def add_outlet(self, name):
        self.add_airconn('air_outlets', name)

    def add_airconn(self, conn, name):
        if getattr(self, conn) is None:
            setattr(self, conn, [name])
        else:
            getattr(self, conn).append(name)

    def create(self):
        subtype = self.type.split(':')[0]
        subsubtype = self.type.split(':')[1]
        # Find type, generally speaking (e.g. fan, coil, terminal unit, etc.)
        if subtype == 'Fan':
            self.addFan()
        elif subtype == 'OutdoorAir':
            self.addOAS()
        elif subtype == 'AirTerminal':
            self.addTerminal()
        elif subtype == 'Coil':
            self.addCoil()
        #elif subtype == 'AirLoopHVAC':
        #    if subsubtype == 'UnitaryHeatPump':
        #        self.addUHP()
        return self

    #### UNITARY SYSTEMS ####

    def addUHP():
        pass

    #### FANS ####

    def addFan(self):
        self.btype = 'Fan'
        self.add_property('fanEfficiency', float(self.idfElement.fan_total_efficiency))
        self.add_property('motorEfficiency', float(self.idfElement.motor_efficiency))
        self.add_property('cooledByFluid', bool(float(self.idfElement.motor_in_airstream_fraction)))
        self.add_inlet(self.idfElement.air_inlet_node_name)
        self.add_outlet(self.idfElement.air_outlet_node_name)
        return self
        #if self.type.split[1] == 'OnOff':
        #    modelicabindings.FanOnOff()

    #### COILS ####

    def addCoil(self):
        self.add_inlet(self.idfElement.air_inlet_node_name)
        self.add_outlet(self.idfElement.air_outlet_node_name)

        if self.type.split(':')[1] == 'Heating':
            self.addHeatingCoil()
        elif self.type.split(':')[1] == 'Cooling':
            self.addCoolingCoil()
    
    def addHeatingCoil(self):
        self.btype = 'Heating_Coil'
    def addCoolingCoil(self):
        self.btype = 'Cooling_Coil'

    #### OA ####

    def addOAS(self):
        if self.type.split(':')[1] == 'Mixer':
            self.btype = 'UndefinedOAS'
            self.add_inlet(self.idfElement.outdoor_air_stream_node_name)
            self.add_inlet(self.idfElement.return_air_stream_node_name)
            self.add_outlet(self.idfElement.mixed_air_node_name)
            self.add_outlet(self.idfElement.relief_air_stream_node_name)

    #### TERMINALS ####

    def addTerminal(self):
        self.add_inlet(self.idfElement.air_inlet_node_name)
        self.add_outlet(self.idfElement.air_outlet_node_name)
        if self.type.split(':')[1] == 'SingleDuct':
            self.SingleDuctTerminal()

    def singleDuctTerminal(self):

        if self.type.split(':')[2] == 'ConstantVolume':
            self.CVTerminal()

    def CVTerminal(self):

        if self.type.split(':')[1] == 'NoReheat':
            self.btype = 'CAV'
            #modelicabindings.CVNoReheat()




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
                if how is 'downstream':
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