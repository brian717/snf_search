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
    # Default to the Sqlite implementation
    # This is an optimization over the standard, CSV implemenatation and
    # is one step closer to a production solution. It saves time and memory
    # by allowing us to filter out providers and deficiences / penalties at
    # query-time, before ever loading them into memory. It is intended to be used
    # with csv_to_sqlite.py, also provided in this package. 
    import sqlite3
    
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    connection = sqlite3.connect("snf.db")
    connection.text_factory = str
    connection.row_factory = dict_factory
    zip_cursor = connection.execute("SELECT * FROM zipcode_mapping")
    # NOTE: for an accurate CDF of overall_ratings / deficiences / penalties,
    # we need to pull in all providers. In reality, we'd want to precompute these 
    # anyway, which would allow us to uncomment the query filters below. 
    provider_cursor = connection.execute("SELECT * FROM provider")# WHERE overall_rating >= ?", (args.min_overall_rating,))
    select_statement = "SELECT p.num AS num, count(*) AS count FROM %s d INNER JOIN provider p ON d.provider_num=p.num GROUP BY p.num"
    deficiencies_cursor = connection.execute(select_statement%"deficiency")
    penalties_cursor = connection.execute(select_statement%"penalty")
    
    zipreader = zip_cursor.fetchall()
    provider_reader = provider_cursor.fetchall()
    deficiencies_reader = deficiencies_cursor.fetchall()
    penalties_reader = penalties_cursor.fetchall()
    
    connection.close()
    
# Read zip code file, creating a dictionary to look up coordinates later...
zip_repository = ZipCodeRepository(zipreader)

# Read providers file, creating provider objects and interning them in Provider.Repository
provider_repository = ProviderRepository(provider_reader)
    
# We're only getting counts of deficiencies / penalties...
# This would need to change if we want to take in the nature of the deficiencies / penalties 
# while computing the score. 
for row in deficiencies_reader:
    provider = provider_repository.get_provider(row)
    # Sql implementation will have already rolled up all rows into a count
    # For CSV, we need to count them one at a time
    provider.num_deficiencies += row["count"] if "count" in row else 1
for row in penalties_reader:
    provider = provider_repository.get_provider(row)
    provider.num_penalties += row["count"] if "count" in row else 1

# If we're using the csv implementation, make sure and close up those files...
if args.csv:
    zipfile.close()
    provider_file.close()
    deficiencies_file.close()
    penalties_file.close()
    
from score import ProviderScorer

scorer = ProviderScorer(provider_repository, zip_repository)

filtered_providers = [p for p in provider_repository.get_all_providers() if p.num_deficiencies < args.max_num_deficiencies and p.num_penalties < args.max_penalties and p.overall_rating > args.min_overall_rating]

scorer.populate_all_scores(filtered_providers, args.zip_code)

filtered_providers.sort(key = lambda p: -p.score)

for p in filtered_providers[:args.num_facilities]:
    print p.toJson()