import sqlite3
import csv
from orm import ModelTableBuilder
from models import *

zipcode_table = ModelTableBuilder(""zipcode_mapping", ZipCodeMappingModel)
provider_table = ModelTableBuilder("provider", ProviderModel, { "provider_overall_rating": ["overall_rating"] })
deficiency_table = ModelTableBuilder("deficiency", DeficiencyModel)
penalty_table = ModelTableBuilder("penalty", [PenaltyModel, FineModel, PaymentDenialModel])

connection = sqlite3.connect("snf.db")
connection.text_factory = str
cursor = connection.cursor()

zipcode_table.create_and_load(cursor, "zip_code_centroids.csv")
provider_table.create_and_load(cursor, "ProviderInfo_Download.csv")
deficiency_table.create_and_load(cursor, "Deficiencies_Download.csv")
penalty_table.create_and_load(cursor, "Penalties_Download.csv")

connection.commit()
connection.close()