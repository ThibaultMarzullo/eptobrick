import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from eptobrick.extractor import epparser
from eptobrick.extractor.objects import ahus

parser = epparser.Extractor()
idf = parser.load(os.path.join(os.path.dirname(__file__), 'resources/ASHRAE901_OfficeSmall_STD2013_Denver.idf'))

parser.bindBuilding(idf)
parser.createAHUs(idf)