# snf_search
Command line tool to search skilled nursing facilities based on a number of criteria, including distance, deficiencies, penalties, and overall rating. 

# Getting started
This tool requires either csv files or a sqlite db file contianing all necessary data to run. This data includes: 

1) A mapping from zip codes to their geographical centers. 
2) A file containing information about the SNF providers. 
3) A file containing information about the penalties incurred by providers. 
4) A file containing information about the deficiencies for each provider. 

# Using CSV files

CSV files for 2, 3, and 4 above can be obtained at: 

https://data.medicare.gov/data/nursing-home-compare

This tool requires that each of csv files contained in the medicare archive reside in the same directory as the tool. 

# Using SQLite
This tool operates much faster and with a lower memory footprint when run against SQLite databases instead of the raw CSV files. For convenience, a dump of the raw CSV files into a SQLite database is provided in the snf.db file. By default, the application will use this file. 

# Regenerating the database
To re-generate the given db file based on updated CSV files, run python csv_to_sqlite.py. This tool also requires that all CSV files to be converted reside in the same directory as the converter. 

#Usage
snf_search.py [-h] [--num_facilities NUM_FACILITIES]
                   [--min_overall_rating {1,2,3,4,5}]
                   [--max_num_deficiencies MAX_NUM_DEFICIENCIES]
                   [--max_penalties MAX_PENALTIES] [--csv]
                   zip_code

Each of the above parameters are named appropriately for their correpsonding fields in the provider data. An additional argument, --csv is added to allow switching between the sqlite (default) implementation and the raw CSV implementation. This is useful if files frequently change and regnerating the db files are not feasible. 

# Scoring providers
Providers are scored based on their overall rating, their number of deficiencies, and the number of penalties assessed against them, as well as the distance from the provided anchor zip code. 

Scores for each metric are obtained by taking the CDF for the given metric and ranking the provider from 0 to 100 based on where they fall on this CDF. As the range for each of the rating, num_deficiencies, and num_penalties metrics are contained within the given data, a simple percentile is used and effectively ranks each provider against the rest based on that metric.

For distance, a CDF for the average american's commute to work is taken from:
https://www.rita.dot.gov/bts/sites/rita.dot.gov.bts/files/publications/omnistats/volume_03_issue_04/pdf/entire.pdf

This is then used to convert distance to a provider into a percentile rank comparing the distance to the average american's commute to work. The rationale here is that this is the distance patients are accustomed to traveling, on average. A score is provided from 0 to 100 based on what percentile the distance to the provider falls within this CDF. For example, a provider that is closer than 90% of americans' daily commute gets a score of 90, while one that is farther than 80% of americans' daily commute gets a score of 20. 

A final score is obtained by taking a weighted sum of each of the above 4 metrics, with equal weighting to each, to obtain a score between 0 and 100 for fitness of a provider. 
