import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from eptobrick.extractor import epparser
from eptobrick.extractor.objects import ahus

parser = epparser.Extractor()
idf = parser.load(os.path.join(os.path.dirname(__file__), 'resources/ASHRAE901_OfficeSmall_STD2013_Denver.idf'))

#print(idf.Fan_OnOff[0])

fan = ahus.AHUComponent(idf.Fan_OnOff[0], 'Fan:OnOff')
#print(fan)
#print(idf.AirLoopHVAC[0])
parser.getListComponents(idf.Branch[0], 'component', 'name')
parser.untangleAirLoopSupply(idf.AirLoopHVAC[0], idf)
parser.untangleAirLoopZones(idf)
#for element in idf.AirLoopHVAC:
#    print(element.branch_list_name)
#
#    parser.walkAirLoop(element)