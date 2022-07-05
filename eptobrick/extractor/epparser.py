import platform, os

import eppy as ep
from eppy.modeleditor import IDF

class Extractor():

    def __init__(self, epdir='/Applications/EnergyPlus-9-6-0') -> None:
        IDF.setiddname(os.path.join(epdir, 'Energy+.idd'))

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
        idf = IDF(eppath)
        return idf
        
