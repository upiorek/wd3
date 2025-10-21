#!/bin/bash

# Check if description argument is provided
if [ $# -eq 0 ]; then
    echo "Error: Description is required!"
    echo "Usage: $0 \"<description>\""
    exit 1
fi

DESCRIPTION="$1"

cd ~/repo
cp -r /var/www/html/ ./
cp -r "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Experts/wd3.mq4" ./
git add .
git commit -m "$DESCRIPTION - $(date +'%Y-%m-%d %H:%M')"
git push origin main

echo "Update completed with description: $DESCRIPTION"