import argparse
import csv
from models import ProviderModel, DeficiencyModel, PenaltyModel, ZipCodeRepository, ProviderRepository

argParser = argparse.ArgumentParser(description="SNF search command line interface.")
argParser.add_argument("zip_code", help="The patient's zip code.")
argParser.add_argument("--num_facilities", dest="num_facilities", type=int, default=20, required=False, help="The maximum number of facilities to return.")
argParser.add_argument("--min_overall_rating", dest="min_overall_rating", type=int, choices=range(1,6), default=1, required=False, help="The minimum allowable overall quality rating for each returned SNF.")
argParser.add_argument("--max_num_deficiencies", dest="max_num_deficiencies", type=float, default=float("inf"), required=False, help="The maximum number of allowable deficiencies for each returned SNF.")
argParser.add_argument("--max_penalties", dest="max_penalties", type=float, default=float("inf"), required=False, help="The maximum number of allowable penalties for each returned SNF.")
argParser.add_argument("--csv", action="store_true")

args = argParser.parse_args()
print args

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

if args.csv:
    zipfile = open("zip_code_centroids.csv", "r")
    zipreader = csv.DictReader(zipfile)
    
    provider_file = open("ProviderInfo_Download.csv", "r")
    provider_reader = csv.DictReader(provider_file)

    deficiencies_file = open("Deficiencies_Download.csv", "r")
    deficiencies_reader = csv.DictReader(deficiencies_file)

    penalties_file = open("Penalties_Download.csv", "r")
    penalties_reader = csv.DictReader(penalties_file)
else:
    import sqlite3
    
    connection = sqlite3.connect("snf.db")
    connection.text_factory = str
    connection.row_factory = dict_factory
    zip_cursor = connection.execute("SELECT * FROM zipcode_mapping")
    provider_cursor = connection.execute("SELECT * FROM provider WHERE overall_rating >= ?", (args.min_overall_rating,))
    provider_reader = provider_cursor.fetchall()
    select_statement = "SELECT p.num AS num, count(*) AS count FROM %s d INNER JOIN provider p ON d.provider_num=p.num WHERE p.overall_rating >= ? GROUP BY p.num"
    deficiencies_cursor = connection.execute(select_statement%"deficiency", (args.min_overall_rating,))
    penalties_cursor = connection.execute(select_statement%"penalty", (args.min_overall_rating,))
    
    zipreader = zip_cursor.fetchall()
    deficiencies_reader = deficiencies_cursor.fetchall()
    penalties_reader = penalties_cursor.fetchall()
    
    connection.close()
    
# Read zip code file, creating a dictionary to look up coordinates later...
zip_repository = ZipCodeRepository(zipreader)

# Read providers file, creating provider objects and interning them in Provider.Repository
provider_repository = ProviderRepository(provider_reader)
    
if args.csv:
    # Read deficiencies file, creating objects and updating the interned providers
    for row in deficiencies_reader:
        DeficiencyModel.update_provider(row, provider_repository)

    # Read penalties file, creating objects and updating the interned providers
    for row in penalties_reader:
        PenaltyModel.update_provider(row, provider_repository)
    zipfile.close()
    provider_file.close()
    deficiencies_file.close()
    penalties_file.close()
else:
    # Using the SQL implementation, we're only getting counts of deficiencies / penalties...
    # This would need to change if we want to take in the nature of the deficiencies / penalties 
    # while computing the score. 
    for row in deficiencies_reader:
        provider = provider_repository.get_provider(row)
        provider.num_deficiencies = row["count"]
    for row in penalties_reader:
        provider = provider_repository.get_provider(row)
        provider.num_penalties = row["count"]
        
filtered_providers = [p for p in provider_repository.get_all_providers() if p.num_deficiencies < args.max_num_deficiencies and p.num_penalties < args.max_penalties and p.overall_rating > args.min_overall_rating]

filtered_providers.sort(key = lambda p: -p.overall_rating)

for p in filtered_providers[:args.num_facilities]:
    print p.toJson()