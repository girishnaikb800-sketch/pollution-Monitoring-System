import os
import sys
import uvicorn
import database
from server import app

def main():
    print("==================================================================")
    print("  🌿 EcoPulse Environmental Pollution Backend Server               ")
    print("==================================================================")
    print("  Database: Neon PostgreSQL Cloud / SQLite local fallback")
    print("  Server URL: http://0.0.0.0:8000")
    print("  Swagger Docs: http://127.0.0.1:8000/docs")
    print("==================================================================")
    
    # Initialize database tables
    database.init_db()
    
    # Start uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
