import argparse
import sqlalchemy as sa
import pandas as pd
import re
import os

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--sqlite-db', required=True, help='Path to the SQLite database file')
parser.add_argument('--mysql-user', required=True, help='MySQL username')
parser.add_argument('--mysql-password', required=True, help='MySQL password')
parser.add_argument('--mysql-host', required=True, help='MySQL host')
parser.add_argument('--mysql-database', required=True, help='MySQL database name')
args = parser.parse_args()

# check if sqlite file exists
if not os.path.exists(args.sqlite_db):
    print(f"Error: SQLite database file {args.sqlite_db} does not exist.")
    exit(1)

# Connect to the SQLite database
engine = sa.create_engine(f'sqlite:///{args.sqlite_db}')

# Create an inspector for the SQLite database
inspector = sa.inspect(engine)

# Get the list of tables in the SQLite database
table_names = inspector.get_table_names()

# Connect to the MySQL database using a SQLAlchemy engine
try:
    mysql_engine = sa.create_engine(f'mysql+mysqlconnector://{args.mysql_user}:{args.mysql_password}@{args.mysql_host}/{args.mysql_database}')
except sa.exc.OperationalError as e:
    if "Access denied for user" in str(e):
        print("Error: Invalid MySQL username or password.")
    else:
        print("Error: Unable to connect to MySQL database.")
    exit(1)

print("Successfully connected to MySQL database.")

# Iterate through the tables in the SQLite database
for table_name in table_names:
    # Drop the table if it already exists in the MySQL database
    mysql_engine.execute(f'DROP TABLE IF EXISTS {table_name}')

    # Load the data for the current table into a pandas DataFrame
    df = pd.read_sql_table(table_name, engine)

    # Remove the "index" column from the DataFrame
    df = df.drop(columns=['index'])

    # Use pandas to generate the CREATE TABLE statement for the table
    create_table_stmt = pd.io.sql.get_schema(df, table_name)

    # Escape the table and column names in the CREATE TABLE statement
    create_table_stmt = re.sub('"([^"]+)"', r'`\1`', create_table_stmt)

    # Execute the CREATE TABLE statement
    mysql_engine.execute(create_table_stmt)

    # Write the data from the DataFrame to the MySQL table
    df.to_sql(table_name, mysql_engine, if_exists='replace', index=False)
    print(f"Table {table_name} inserted.")
