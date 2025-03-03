import os
import psycopg2
from urllib.parse import urlparse

def test_connection():
    try:
        # Get DATABASE_URL from environment variable
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        if not DATABASE_URL:
            print("ERROR: DATABASE_URL environment variable not set")
            return False
            
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a simple test query
        cur.execute('SELECT version();')
        
        # Fetch the result
        version = cur.fetchone()
        print("Successfully connected to the database!")
        print(f"PostgreSQL version: {version[0]}")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return False

if __name__ == "__main__":
    test_connection() 