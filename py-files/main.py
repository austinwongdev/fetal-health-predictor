"""
Austin Wong
001355444
2/22/2021
"""

# IMPORTS
import sys

# Custom Packages
from window import controller, create_alert
from dbinter import start_conn, close_conn


if __name__ == '__main__':

    # Connect to SQLite DB
    conn = start_conn()
    if conn is None:
        create_alert('Could not connect to database. Try again later or contact administrator.', 'Error', 'salmon')
        sys.exit()

    # Create GUI
    controller(conn)

    # Close SQLite DB Connection
    close_conn(conn)
