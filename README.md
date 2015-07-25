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
