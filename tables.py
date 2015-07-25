import sqlite3
import csv

ZIPCODE_TABLE = {
    "name": "zipcode_mapping",
    "csv_filename": "zip_code_centroids.csv",
    "columns": [
        ("zip", "TEXT PRIMARY KEY", "zip_code"),
        ("lat", "REAL"),
        ("lng", "REAL")
    ]
}

PROVIDER_TABLE = {
    "name": "provider",
    "csv_filename": "ProviderInfo_Download.csv",
    "columns": [
        ("num", "TEXT PRIMARY KEY", "provnum"),
        ("name", "TEXT", "PROVNAME"),
        ("address", "TEXT", "ADDRESS"),
        ("city", "TEXT", "CITY"),
        ("state", "TEXT", "STATE"),
        ("zip", "TEXT REFERENCES zipcode_mapping(zip)", "ZIP"),
        ("phone", "TEXT", "PHONE"),
        ("overall_rating", "INTEGER")
    ],
    #"preprocessing": {
    #    "overall_rating": lambda v: int(v) if len(v) > 0 else None
    #}
}

DEFICIENCY_TABLE = {
    "name": "deficiency", 
    "csv_filename": "Deficiencies_Download.csv",
    "columns": [
        ("provider_num", "INTEGER REFERENCES provider(num)", "provnum"),
        ("survey_date", "TEXT", "survey_date_output"),
        ("survey_type", "TEXT", "SurveyType")
    ]
}

PENALTY_TABLE = {
    "name": "penalty",
    "csv_filename": "Penalties_Download.csv",
    "columns":  [
        ("provider_num", "INTEGER REFERENCES provider(num)", "provnum"),
        ("penalty_date", "TEXT", "pnlty_date"),
        ("file_date", "TEXT", "filedate"),
        ("type", "TEXT", "pnlty_type"),
        ("fine_amount", "REAL NULL", "fine_amt"),
        ("payment_denial_start_date", "TEXT NULL", "payden_strt_dt"),
        ("payment_denial_days", "INTEGER NULL", "payden_days")
    ]
}

TABLES = [
    ZIPCODE_TABLE,
    PROVIDER_TABLE,
    DEFICIENCY_TABLE,
    PENALTY_TABLE
]

def get_column_definition(table):
    return ", ".join(["%s %s"%(c[0], c[1]) for c in table["columns"]])

def get_create_table_statement(table):
    return "CREATE TABLE IF NOT EXISTS %s(%s)" % (table["name"], get_column_definition(table))

def project_value(table, col, row):
    #if "preprocessing" in table:
    #    print "%s, %s, %s"%(table, col, row)
    return table["preprocessing"][col](row[col]) if "preprocessing" in table and col in table["preprocessing"] else row[col]
    
def project_values_from_csv(table, reader):
    csv_column_names = [c[2] if len(c) > 2 else c[0] for c in table["columns"]]
    for row in reader:
        #print [row[col] for col in csv_column_names]
        yield [project_value(table, col, row) for col in csv_column_names]

        
def create_table(connection, table):
    cur = connection.cursor()
    cur.execute(get_create_table_statement(table))
    csv_file = open(table["csv_filename"], "r")
    csv_reader = csv.DictReader(csv_file)
    column_names = ", ".join([c[0] for c in table["columns"]])
    wildcards = ",".join("?"*len(table["columns"]))
    cur.executemany("insert into %s(%s) values(%s)"%(table["name"], column_names, wildcards), project_values_from_csv(table, csv_reader))
    connection.commit()
    
connection = sqlite3.connect("snf.db")

for table in TABLES:
    print table["name"]
    create_table(connection, table)

connection.close()