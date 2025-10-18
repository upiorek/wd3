cd ~/repo
cp -r /var/www/html/ ./
cp -r "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Experts/wd3.mq4" ./
git add .
git commit -m "Auto-update $(date +'%Y-%m-%d %H:%M')"
git push origin main