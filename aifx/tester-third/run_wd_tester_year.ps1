
for ($i = 1; $i -le 12; $i++) {
    $i2 = $i.ToString("00")
    python3 process_candles.py --input-dir ../data/2025.$i2 --mt --no-images
}

for ($i = 1; $i -le 12; $i++) {
    $i2 = $i.ToString("00")

    # version with no copying data 
    # python3 .\run_mt4_tester.py wd_tester --month $i --no-copy-data

    # copy data before running tester
    python3 .\run_mt4_tester.py wd_tester --month $i --input-dir "aifx\data\2025.$i2\charts"
}
