import os
import psycopg2
from dotenv import load_dotenv
from typing import List, Dict
import sys

def load_db_config() -> Dict[str, str]:
    """Load database configuration from .env file."""
    load_dotenv()
    
    required_vars = [
        'RDS_USER',
        'RDS_PASSWORD',
        'RDS_HOST',
        'RDS_PORT',
        'RDS_DB'
    ]
    
    # Check if all required variables are present
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
        
    return {
        'user': os.getenv('RDS_USER'),
        'password': os.getenv('RDS_PASSWORD'),
        'host': os.getenv('RDS_HOST'),
        'port': os.getenv('RDS_PORT'),
        'database': os.getenv('RDS_DB')
    }

def get_connection(config: Dict[str, str]):
    """Create database connection."""
    try:
        return psycopg2.connect(**config)
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def get_available_extensions(conn) -> List[Dict]:
    """Get list of available extensions."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, default_version, installed_version, comment 
                FROM pg_available_extensions 
                ORDER BY name;
            """)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    except psycopg2.Error as e:
        print(f"Error fetching extensions: {e}")
        return []

def get_installed_extensions(conn) -> List[str]:
    """Get list of already installed extensions."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT extname FROM pg_extension;")
            return [row[0] for row in cur.fetchall()]
    except psycopg2.Error as e:
        print(f"Error fetching installed extensions: {e}")
        return []

def install_extension(conn, extension_name: str) -> bool:
    """Install a specific extension."""
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE EXTENSION IF NOT EXISTS {extension_name};")
            conn.commit()
            print(f"Successfully installed extension: {extension_name}")
            return True
    except psycopg2.Error as e:
        print(f"Error installing extension {extension_name}: {e}")
        conn.rollback()
        return False

def main():
    # Load configuration
    config = load_db_config()
    
    # Connect to database
    print("Connecting to database...")
    conn = get_connection(config)
    
    # Get available extensions
    print("\nFetching available extensions...")
    available_extensions = get_available_extensions(conn)
    print("\nAvailable extensions:")
    for ext in available_extensions:
        print(f"- {ext['name']}: {ext['comment']}")
        print(f"  Default version: {ext['default_version']}")
        print(f"  Installed version: {ext['installed_version'] or 'Not installed'}")
        print()

    # Get installed extensions
    installed = get_installed_extensions(conn)
    print("\nCurrently installed extensions:", ", ".join(installed))

    # Define extensions we want to install
    desired_extensions = [
        'vector',
        'pgrouting',  # Graph functionality
        'postgis',     # Geospatial support
        'postgres_fdw' # Foreign data wrapper
    ]
    
    # Install desired extensions if not already installed
    print("\nChecking and installing required extensions...")
    for ext_name in desired_extensions:
        if ext_name in [ext['name'] for ext in available_extensions]:
            if ext_name not in installed:
                print(f"\nInstalling {ext_name}...")
                install_extension(conn, ext_name)
            else:
                print(f"\n{ext_name} is already installed.")
        else:
            print(f"\n{ext_name} is not available in your region/setup.")

    # Install compatible graph extension
    install_extension(conn, 'pgRouting')  # Available as 'pgrouting' in your list

    # Close connection
    conn.close()
    print("\nDatabase connection closed.")

if __name__ == "__main__":
    main() 