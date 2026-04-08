#!/usr/bin/env python3
"""
Portfolio Analytics Tool - Setup Script
======================================

One-time setup for the Portfolio Analytics Tool.
Run this after cloning/downloading the project.

This script will:
1. Check Python version
2. Install dependencies
3. Initialize database
4. Verify installation
"""

import sys
import subprocess
import os

def check_python_version():
    """Check if Python 3.10+ is installed"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python {version.major}.{version.minor} found.")
        print("   Required: Python 3.10 or higher")
        print("   Please upgrade Python: https://www.python.org/downloads/")
        return False
    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} found")
    return True

def install_dependencies():
    """Install required packages"""
    print("\n📦 Installing dependencies...")
    
    requirements = [
        'streamlit>=1.28.0',
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'plotly>=5.18.0',
        'PyPDF2>=3.0.0',
        'pdfplumber>=0.10.0',
        'pyyaml>=6.0.1',
        'requests>=2.31.0',
        'scipy>=1.11.0'
    ]
    
    try:
        # Try to install from requirements.txt first
        if os.path.exists('requirements.txt'):
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                         check=True, capture_output=True)
        else:
            # Install individual packages
            subprocess.run([sys.executable, '-m', 'pip', 'install'] + requirements, 
                         check=True, capture_output=True)
        
        print("   ✅ All dependencies installed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to install dependencies")
        print(f"   Error: {e}")
        return False

def initialize_database():
    """Initialize SQLite database"""
    print("\n🗄️  Initializing database...")
    
    try:
        # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from database import PortfolioDatabase
        db = PortfolioDatabase()
        db.initialize_database()
        
        print("   ✅ Database initialized")
        print(f"   📁 Location: {os.path.abspath(db.db_path)}")
        return True
        
    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        return False

def verify_installation():
    """Verify all components are working"""
    print("\n🧪 Verifying installation...")
    
    checks = []
    
    # Check imports
    try:
        import streamlit
        import pandas
        import numpy
        import plotly
        import yaml
        import requests
        print("   ✅ Python packages imported")
        checks.append(True)
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        checks.append(False)
    
    # Check database
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from database import PortfolioDatabase
        db = PortfolioDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        print(f"   ✅ Database accessible ({len(tables)} tables)")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        checks.append(False)
    
    # Check config files
    try:
        configs = ['config/categories.yaml', 'config/limits.yaml', 'config/glide_path.yaml']
        for cfg in configs:
            with open(cfg, 'r') as f:
                yaml.safe_load(f)
        print("   ✅ Configuration files valid")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ Config check failed: {e}")
        checks.append(False)
    
    return all(checks)

def print_next_steps():
    """Print instructions for next steps"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("\n1. Launch the dashboard:")
    print("   streamlit run app.py")
    print("\n2. Or run with sample data:")
    print("   python3 app.py sample")
    print("   streamlit run app.py")
    print("\n3. Upload your CAS statement:")
    print("   - Get CAS from CAMS/Karvy/NSDL")
    print("   - Upload via sidebar in dashboard")
    print("\n4. Add FD/PPF/NPS:")
    print("   - Use CSV templates in templates/ folder")
    print("   - Upload via 'Upload Manual Assets' tab")
    print("\n📚 Documentation:")
    print("   docs/USER_GUIDE.md - Complete user manual")
    print("\n⚙️  Configuration:")
    print("   config/limits.yaml    - Alert thresholds")
    print("   config/glide_path.yaml - Age-based allocation")
    print("\n🆘 Help:")
    print("   python3 app.py help")
    print("\n" + "="*60)

def main():
    """Main setup flow"""
    print("="*60)
    print("  Portfolio Analytics Tool - Setup")
    print("="*60)
    
    # Step 1: Check Python
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n⚠️  Try installing manually:")
        print("   pip install streamlit pandas numpy plotly pyyaml requests PyPDF2 pdfplumber")
        sys.exit(1)
    
    # Step 3: Initialize database
    if not initialize_database():
        sys.exit(1)
    
    # Step 4: Verify
    if not verify_installation():
        print("\n⚠️  Verification failed. Check error messages above.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Step 5: Print next steps
    print_next_steps()

if __name__ == '__main__':
    main()
