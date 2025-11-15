"""
Download and setup 32-bit Python embeddable for DLL compilation
"""
import urllib.request
import zipfile
import os
import sys

PYTHON_32BIT_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-win32.zip"
PYTHON_32BIT_DEV_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
DOWNLOAD_DIR = "python32_embed"

def download_python32():
    """Download 32-bit embeddable Python"""
    print("\n" + "="*60)
    print("DOWNLOADING 32-BIT PYTHON FOR DLL COMPILATION")
    print("="*60)
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    zip_path = os.path.join(DOWNLOAD_DIR, "python311_32bit.zip")
    
    if os.path.exists(zip_path):
        print(f"\n✓ Already downloaded: {zip_path}")
    else:
        print(f"\nDownloading from: {PYTHON_32BIT_URL}")
        print("Please wait...")
        
        try:
            urllib.request.urlretrieve(PYTHON_32BIT_URL, zip_path)
            print(f"✓ Downloaded: {zip_path}")
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return False
    
    # Extract
    extract_dir = os.path.join(DOWNLOAD_DIR, "python311")
    if os.path.exists(extract_dir):
        print(f"✓ Already extracted: {extract_dir}")
    else:
        print(f"\nExtracting to: {extract_dir}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"✓ Extracted Python 3.11 (32-bit)")
    
    # We need the development files (headers and libs)
    print("\n" + "="*60)
    print("IMPORTANT: To compile the DLL, you need:")
    print("="*60)
    print("1. Download Python 3.11.9 32-bit installer from:")
    print("   https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe")
    print("\n2. Run installer and select:")
    print("   - Install for all users")
    print("   - Customize installation")
    print("   - Check 'py launcher' and 'for all users'")
    print("   - Advanced: Check 'Install for all users' and 'Download debug binaries'")
    print("   - Install location: C:\\Python311-32")
    print("\n3. After installation, the build script will work")
    print("="*60)
    
    return True

if __name__ == "__main__":
    download_python32()
