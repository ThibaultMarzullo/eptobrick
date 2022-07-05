import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from eptobrick.extractor import epparser

parser = epparser.Extractor()
parser.load(os.path.join(os.path.dirname(__file__), 'resources/ASHRAE901_Hospital_STD2016_Denver.idf'))