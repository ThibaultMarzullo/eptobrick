from ..utils import utils as ut

class AHUComponent():

    def __init__(self, idfobj, objtype) -> None:
        
        #define base properties here
        self.idfElement = idfobj
        self.name = idfobj.name.replace(' ', '~')
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
            self.addFan(subsubtype)
        elif subtype == 'OutdoorAir':
            self.addOAS()
        elif subtype == 'AirTerminal':
            self.addTerminal()
        elif subtype == 'Coil':
            self.addCoil()
        elif subtype == 'AirLoopHVAC':
            if subsubtype == 'ZoneSplitter':
                self.addSplitter()
            elif subsubtype == 'ZoneMixer':
                self.addMixer()
            elif subsubtype == 'ReturnPlenum':
                self.addReturnPlenum()
        #elif subtype == 'AirLoopHVAC':
        #    if subsubtype == 'UnitaryHeatPump':
        #        self.addUHP()
        return self

    #### UNITARY SYSTEMS ####

    def addUHP():
        pass

    #### FANS ####

    def addFan(self, subtype):
        
        self.add_property('fanEfficiency', float(self.idfElement.fan_total_efficiency))
        self.add_inlet(self.idfElement.air_inlet_node_name)
        self.add_outlet(self.idfElement.air_outlet_node_name)

        if subtype == 'OnOff':
            self.btype = 'Fan'
            self.add_property('motorEfficiency', float(self.idfElement.motor_efficiency))
            self.add_property('cooledByFluid', bool(float(self.idfElement.motor_in_airstream_fraction)))
        if subtype == 'ZoneExhaust':
            self.btype = 'Exhaust_Fan'
        if subtype == 'VariableVolume':
            self.btype = 'Fan'

        
        
        return self

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
            self.btype = 'HVAC_Equipment'
            self.add_inlet(self.idfElement.outdoor_air_stream_node_name)
            self.add_inlet(self.idfElement.return_air_stream_node_name)
            self.add_outlet(self.idfElement.mixed_air_node_name)
            self.add_outlet(self.idfElement.relief_air_stream_node_name)

    #### TERMINALS ####

    def addTerminal(self):
        self.add_inlet(self.idfElement.air_inlet_node_name)
        self.add_outlet(self.idfElement.air_outlet_node_name)
        if self.type.split(':')[1] == 'SingleDuct':
            self.singleDuctTerminal()

    def singleDuctTerminal(self):

        if self.type.split(':')[2] == 'ConstantVolume':
            self.CAVTerminal()
        if self.type.split(':')[2] == 'VAV':
            self.VAVTerminal()
        

    def CAVTerminal(self):
        self.btype = 'CAV'
        if self.type.split(':')[1] == 'NoReheat':
            pass
            #modelicabindings.CVNoReheat()
    
    def VAVTerminal(self):
        self.btype = 'VAV'
        self.air_outlets = [] # get rid of outlets, or the Damper will be bypassed
        self.add_outlet(self.idfElement.damper_air_outlet_node_name)
        if self.type.split(':')[1] == 'NoReheat':
            pass
        if self.type.split(':')[1] == 'Reheat':
            
            pass

    #### OTHER ZONE EQUIPMENT ####

    def addSplitter(self):
        for outlet in ut.getListComponents(self.idfElement, 'outlet', 'node_name'):
            self.add_outlet(outlet)
        self.add_inlet(self.idfElement.inlet_node_name)

    def addMixer(self):
        for inlet in ut.getListComponents(self.idfElement, 'inlet', 'node_name'):
            self.add_inlet(inlet)
        self.add_outlet(self.idfElement.outlet_node_name)

    def addReturnPlenum(self):
        self.btype = 'Air_Plenum'
        self.add_outlet(self.idfElement.outlet_node_name)
        for inlet in ut.getListComponents(self.idfElement, 'inlet', 'node_name'):
            self.add_inlet(inlet)

    def addSupplyPlenum():
        print("Hello, I am a supply plenum. Please implement me!")
        pass

class ThermalZone(AHUComponent):

    def __init__(self, idfobj, objtype, inlets, outlets) -> None:
        self.idfElement = idfobj
        self.name = idfobj.zone_name.name
        self.type = objtype
        self.air_inlets = inlets
        self.air_outlets = outlets
        self.data = {}
        self.btype = None

    def create(self):
        self.btype = 'HVAC_Zone'
        return self
