"""
One-time database setup script.
Creates gem_user and gem_compliance database.
Run: python setup_db.py
"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='', dbname='postgres')
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute("CREATE USER gem_user WITH PASSWORD 'gem_password'")
    print("Created user gem_user")
except Exception as e:
    print(f"User: {e}")

try:
    cur.execute("CREATE DATABASE gem_compliance OWNER gem_user")
    print("Created database gem_compliance")
except Exception as e:
    print(f"Database: {e}")

try:
    cur.execute("GRANT ALL PRIVILEGES ON DATABASE gem_compliance TO gem_user")
    print("Granted privileges")
except Exception as e:
    print(f"Grant: {e}")

cur.close()
conn.close()
print("Database setup complete.")
