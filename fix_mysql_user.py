"""
Script to create a MySQL user with remote access permissions.
Run this locally, then update your CapRover environment variables.
"""
import pymysql
import os

# Get MySQL connection details
mysql_host = input("Enter MySQL host (default: srv-captain--stewardwell-db): ").strip() or 'srv-captain--stewardwell-db'
mysql_port = int(input("Enter MySQL port (default: 3306): ").strip() or '3306')
mysql_root_password = input("Enter MySQL root password: ").strip()

print("\nAttempting to connect to MySQL...")

try:
    # Try connecting as root from localhost perspective
    # This might work if we're running this script in a container on the same network
    connection = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        user='root',
        password=mysql_root_password,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    print("✓ Connected to MySQL successfully!")
    
    with connection.cursor() as cursor:
        # Create stewardwell database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS stewardwell")
        print("✓ Database 'stewardwell' exists")
        
        # Create a new user that can connect from any host
        new_user = 'stewardwell'
        new_password = input(f"\nEnter password for new user '{new_user}': ").strip()
        
        # Drop user if exists and recreate
        cursor.execute(f"DROP USER IF EXISTS '{new_user}'@'%'")
        cursor.execute(f"CREATE USER '{new_user}'@'%' IDENTIFIED BY '{new_password}'")
        print(f"✓ Created user '{new_user}'@'%'")
        
        # Grant all privileges on stewardwell database
        cursor.execute(f"GRANT ALL PRIVILEGES ON stewardwell.* TO '{new_user}'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        print(f"✓ Granted all privileges on stewardwell database")
        
        # Verify the user was created
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User = %s", (new_user,))
        result = cursor.fetchone()
        print(f"✓ User verified: {result}")
        
    connection.commit()
    connection.close()
    
    print("\n" + "="*60)
    print("SUCCESS! Now update your CapRover environment variables:")
    print("="*60)
    print(f"MYSQL_USER={new_user}")
    print(f"MYSQL_PASSWORD={new_password}")
    print("="*60)
    
except pymysql.err.OperationalError as e:
    print(f"\n✗ Connection failed: {e}")
    print("\nThis script needs to run from a container that can access the MySQL database.")
    print("Since CapRover doesn't provide terminal access, try this alternative:")
    print("\n1. Delete your stewardwell-db app in CapRover")
    print("2. Recreate it with MYSQL_ROOT_HOST=% set from the start")
    print("3. Or use a different MySQL service that allows remote root access")
except Exception as e:
    print(f"\n✗ Error: {e}")
