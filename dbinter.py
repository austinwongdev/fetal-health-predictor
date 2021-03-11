"""
Austin Wong
001355444
2/22/2021
"""

# IMPORTS
# Database
import sqlite3 as sql
from sqlite3 import Error

# General
from os import path
from pathlib import Path
import datetime


# CLASSES
class DBInter:
    """
    Class for easy access to database connection info
    """
    conn = None
    current_user = None


# GETTERS AND SETTERS
def set_conn(conn):
    """
    Set database connection
    :param conn: SQLite3 Connection object
    :return: None
    """
    DBInter.conn = conn


def get_conn():
    """
    Get current database connection
    :return: Current SQLite3 Connection object
    """
    return DBInter.conn


def set_current_user(user):
    """
    Set current user connected to database
    :param user: String (username)
    :return: None
    """
    DBInter.current_user = user


def get_current_user():
    """
    Gets current user connected to the database
    :return: String of current user's username
    """
    return DBInter.current_user


# FUNCTIONS
def start_conn():
    """
    Establishes connection to SQLite database. Logs error if unsuccessful.
    :return: Connection object if successful, None if unsuccessful
    """

    dirname = Path(__file__).parent.absolute()
    db_filepath = Path(dirname, 'fetal_health_db').with_suffix('.db')
    error_filepath = Path(dirname, 'error_log').with_suffix('.txt')

    if path.exists(db_filepath) is False:
        f = open(error_filepath, 'a')
        f.write('{} - Cannot find database file\n'.format(datetime.datetime.now()))
        f.close()
        return None

    try:
        conn = sql.connect(db_filepath)
        set_conn(conn)

    except Error as e:
        f = open(error_filepath, 'a')
        f.write('{} - {}\n'.format(datetime.datetime.now(), e))
        f.close()
        return None

    return conn


def close_conn(conn):
    """
    Closes connection to SQLite DB
    :param conn: Connection object
    :return: None
    """
    set_conn(None)

    dirname = Path(__file__).parent.absolute()
    error_filepath = Path(dirname, 'error_log').with_suffix('.txt')

    try:
        conn.close()
    except Error as e:
        f = open(error_filepath, 'a')
        f.write('{} - {}\n'.format(datetime.datetime.now(), e))
        f.close()
    except Exception as exc:
        f = open(error_filepath, 'a')
        f.write('{} - {}\n'.format(datetime.datetime.now(), exc))
        f.close()


def attempt_login(username, password, conn):
    """
    Verifies credentials with user table in database and checks if user is active
    :param username: userName (string)
    :param password: password (string)
    :param conn: Connection object to database
    :return: 1 if user is active and credentials are correct, 0 otherwise
    """

    try:
        query = "SELECT COUNT(*) FROM user WHERE userName = ? AND password = ? AND active=TRUE"
        placeholder = (username, password)
        cur = conn.cursor()
        cur.execute(query, placeholder)
        result = cur.fetchone()[0]
    except Error as e:

        dirname = Path(__file__).parent.absolute()
        error_filepath = Path(dirname, 'error_log').with_suffix('.txt')

        f = open(error_filepath, 'a')
        f.write('{} - {}\n'.format(datetime.datetime.now(), e))
        f.close()
        return 0
    return result
