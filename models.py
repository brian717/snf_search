
from math import radians, cos, sin, asin, sqrt
from orm import ModelField, Model, SQL_MODEL_UNION

def haversine(lon1, lat1, lon2, lat2, si = False):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 if si else 3956 # Radius of earth in kilometers if si, miles if not
    return c * r
    
class ZipCodeRepository(object):
    """
    A repository for mappings between zip codes and their lat, long centers. 
    """
    def __init__(self, zipreader):
        """Initializes a ZipCodeRepository with a given dictionary reader.
        
        Arguments:
            zipreader - A sequence of dictionaries containing zip_code, lat, and lng attributes.
        """
        self.ziphash = { z["zip_code"] : ZipCodeMappingModel(z) for z in zipreader }
        
    def get_distance_between(self, zip1, zip2):
        """
        Gets the distance in miles between two zip code strings. 
        """
        if zip1 not in self.ziphash or zip2 not in self.ziphash:
            return float("inf")
        coords1 = self.ziphash[zip1]
        coords2 = self.ziphash[zip2]
        return haversine(coords1.lng, coords1.lat, coords2.lng, coords2.lat)
    
    def get(self, zip):
        """
        Gets the zip code mapping corresponding to the given zip code string. 
        """
        return self.ziphash[zip]

class ZipCodeMappingModel(Model):
    """
    Represents a mapping between a zip code string and its geographical center.
    """
    zip_code = ModelField("zip_code", key=True, sqltype="TEXT PRIMARY KEY")
    lat = ModelField("lat", type=float, sqltyp="REAL")
    lng = ModelField("lng", type=float, sqltype="REAL")
        
class ProviderRepository(object):
    """
    A repository for ProviderModel objects. 
    """
    def __init__(self, provider_reader):
        """
        Populates a ProviderRepository with providers from a sequence of dictionaries containing data
        to construct the ProviderModels. Typically obtained by reading a CSV file or SQL query.
        """
        self.provider_hash = {}
        for row in provider_reader:
            num = ProviderModel.get_key(row)
            self.provider_hash[num] = ProviderModel(row)
    
    def get_provider(self, rowdict):
        """
        Gets the provider corresponding to the key in the given row dictionary.
        ProviderModels are keyed on the num field.
        """
        num = ProviderModel.get_key(rowdict)
        return self.provider_hash.get(num, None) 
    
    def get_all_providers(self):
        """Gets a view to all providers contained in this repository."""
        return self.provider_hash.viewvalues()

class ProviderModel(Model):
    """
    Represents a skilled nursing facility / provider, including identifying information and metadata about the provider.
    """
    num = ModelField("num", ["provnum", "provider_num"], key = True, sqltype="TEXT PRIMARY KEY")
    name = ModelField("name", ["PROVNAME"], sqltype="TEXT")
    street = ModelField("street", ["ADDRESS", "address"], sqltype="TEXT")
    city = ModelField("city", ["CITY"], sqltype="TEXT")
    state = ModelField("state", ["STATE"], sqltype="TEXT")
    zip = ModelField("zip", ["ZIP"], sqltype="TEXT REFERENCES zipcode_mapping(zip_code)")
    phone = ModelField("phone", ["PHONE"], sqltype="TEXT")
    overall_rating = ModelField("overall_rating", type = int, default = 0, sqltype="INTEGER")
    
    def __init__(self, *args, **kwargs):
        """
        Initializes a ProviderModel and sets the number of deficiencies and penalties to zero. 
        These values must be updated when the corresponding data are read in for those Models. 
        """
        super(ProviderModel, self).__init__(*args, **kwargs)
        self.num_deficiencies = 0
        self.num_penalties = 0
        
class DeficiencyTypeModel(Model):
    """
    Represents a type of deficiency, as well as a repository for these types.
    Interning in a repo is necessary to save memory space as the number of deficiencies is very large. 
    """
    tag = ModelField("tag", key = True, sqltype="TEXT")
    survey_type = ModelField("survey_type", ["SurveyType"], sqltype="TEXT")
    desc  = ModelField("desc", ["tag_desc"], sqltype="TEXT")
    defpref = ModelField("defpref", sqltype="TEXT")    
    
    TypeHash = {}
    
    @classmethod
    def get(cls,rowdict):
        """Gets the DeficiencyTypeModel corresponding to the key in a given row dictionary, creating it if necessary."""
        tag = rowdict["tag"]
        if tag not in cls.TypeHash:
            cls.TypeHash[tag] = cls(rowdict)
        return cls.TypeHash[tag]

class DeficiencyModel(Model):
    """Represents a deficiency marked on a provider."""
    provider_num = ModelField("provider_num", ["provnum"], sqltype="TEXT REFERENCES provider(num)")
    survey_date = ModelField("survey_date", ["survey_date_output"], sqltype="TEXT")
    deficiency_type = ModelField("deficiency_type", None, DeficiencyTypeModel, sqltype=SQL_MODEL_UNION)
    
    @classmethod
    def create_and_update_provider(cls, rowdict, provider_repo):
        """Creates a deficiency and updates the corresponding provider from the given repo."""
        deficiency = cls(rowdict)
        cls.update_provider()
        return deficiency
    
    @classmethod
    def update_provider(cls, rowdict, provider_repo):
        """
        Updates the provider corresponding to the deficiency passed in within the row dictionary.
        This does not create a DeficiencyModel object. 
        """
        provider = provider_repo.get_provider(rowdict)
        provider.num_deficiencies += 1

class PenaltyModel(Model):
    """Represents a penalty assessed on a Provider."""
    provider_num = ModelField("provider_num", ["provnum"], sqltype="TEXT REFERENCES provider(num)")
    penalty_date = ModelField("penalty_date", ["pnlty_date"], sqltype="TEXT")
    file_date = ModelField("file_date", ["filedate"], sqltype="TEXT")
    type = ModelField("type", ["pnlty_type"], key = True, sqltype="TEXT")
    
    @classmethod
    def create_and_update_provider(cls, rowdict, provider_repo):
        """Creates a penalty and updates the corresponding provider from the given repo."""
        penalty_type = cls.get_key(rowdict)
        penalty = None
        if penalty_type == "fine":
            penalty = FineModel(rowdict)
        elif penalty_type == "payment denial":
            penalty = PaymentDenialModel(rowdict)
        cls.update_provider(rowdict, provider_repo)
        
        return penalty
        
    @classmethod
    def update_provider(cls, rowdict, provider_repo):
        """
        Updates the provider corresponding to the penalty passed in within the row dictionary.
        This does not create a PenaltyModel object. 
        """
        provider = provider_repo.get_provider(rowdict)
        provider.num_penalties += 1

class FineModel(PenaltyModel):
    """A PenaltyModel that represents a Fine assessed against a provider."""
    amount = ModelField("fine_amount", ["fine_amt", "amount"], sqltype="REAL NULL")

class PaymentDenialModel(PenaltyModel):
    """A PenaltyModel that represents a Payment Denial assessed against a provider."""
    start_date = ModelField("payment_denial_start_date", ["payden_strt_dt", "start_date"], sqltype="TEXT NULL"),
    days = ModelField("payment_denial_days", ["payden_days", "days"], sqltype="INTEGER NULL")
