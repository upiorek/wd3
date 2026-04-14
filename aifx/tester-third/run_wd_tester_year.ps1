

cd C:\rrudnick\wd3\aifx\tester-third
for ($i = 1; $i -le 12; $i++) {
    $i2 = $i.ToString("00")
    python3 process_candles.py --input-dir ../data/2025.$i2 --clean
}

cd C:\rrudnick\wd3\aifx\tester-third
for ($i = 1; $i -le 12; $i++) {
    $i2 = $i.ToString("00")
    python3 process_candles.py --input-dir ../data/2025.$i2 --mt --no-images
}

for ($i = 1; $i -le 12; $i++) {
    $i2 = $i.ToString("00")

    # version with no copying data 
    # python3 .\run_mt4_tester.py wd_tester --month $i --no-copy-data

    # call decisioner
    # python3 process_candles.py --input-dir ../data/2025.$i2 --mt --no-images --keep-results

    # copy data before running tester
    python3 .\run_mt4_tester.py wd_tester --month $i --input-dir "aifx\data\2025.$i2\charts"
}

python3 .\run_mt4_tester.py wd_tester --month 1 --input-dir "aifx\data\2025.01\charts"
python3 .\run_mt4_tester.py wd_tester --month 2 --input-dir "aifx\data\2025.02\charts"
python3 .\run_mt4_tester.py wd_tester --month 3 --input-dir "aifx\data\2025.03\charts"
python3 .\run_mt4_tester.py wd_tester --month 4 --input-dir "aifx\data\2025.04\charts"
python3 .\run_mt4_tester.py wd_tester --month 5 --input-dir "aifx\data\2025.05\charts"
python3 .\run_mt4_tester.py wd_tester --month 6 --input-dir "aifx\data\2025.06\charts"
python3 .\run_mt4_tester.py wd_tester --month 7 --input-dir "aifx\data\2025.07\charts"
python3 .\run_mt4_tester.py wd_tester --month 8 --input-dir "aifx\data\2025.08\charts"
python3 .\run_mt4_tester.py wd_tester --month 9 --input-dir "aifx\data\2025.09\charts"
python3 .\run_mt4_tester.py wd_tester --month 10 --input-dir "aifx\data\2025.10\charts"
python3 .\run_mt4_tester.py wd_tester --month 11 --input-dir "aifx\data\2025.11\charts"
python3 .\run_mt4_tester.py wd_tester --month 12 --input-dir "aifx\data\2025.12\charts"

# cleanup + retest 01

cd C:\rrudnick\wd3\aifx\tester-third
python3 process_candles.py --input-dir ../data/2025.01 --clean
python3 process_candles.py --input-dir ../data/2025.01 --mt --no-images
python3 .\run_mt4_tester.py wd_tester --month 1 --input-dir "aifx\data\2025.01\charts"

# last 3 months

cd C:\rrudnick\wd3\aifx\tester-third
python3 process_candles.py --input-dir ../data/2025.10 --clean
python3 process_candles.py --input-dir ../data/2025.11 --clean
python3 process_candles.py --input-dir ../data/2025.12 --clean
python3 process_candles.py --input-dir ../data/2026.01 --clean
python3 process_candles.py --input-dir ../data/2026.02 --clean
python3 process_candles.py --input-dir ../data/2026.03 --clean
python3 process_candles.py --input-dir ../data/2025.10 --mt --no-images
python3 process_candles.py --input-dir ../data/2025.11 --mt --no-images
python3 process_candles.py --input-dir ../data/2025.12 --mt --no-images
python3 process_candles.py --input-dir ../data/2026.01 --mt --no-images
python3 process_candles.py --input-dir ../data/2026.02 --mt --no-images
python3 process_candles.py --input-dir ../data/2026.03 --mt --no-images

cd C:\rrudnick\wd3\aifx\tester-third
python3 .\run_mt4_tester.py wd_tester --month 10 --input-dir "aifx\data\2025.10\charts"
python3 .\run_mt4_tester.py wd_tester --month 11 --input-dir "aifx\data\2025.11\charts"
python3 .\run_mt4_tester.py wd_tester --month 12 --input-dir "aifx\data\2025.12\charts"
python3 .\run_mt4_tester.py wd_tester --year 2026 --month 01 --input-dir "aifx\data\2026.01\charts"
python3 .\run_mt4_tester.py wd_tester --year 2026 --month 02 --input-dir "aifx\data\2026.02\charts"
python3 .\run_mt4_tester.py wd_tester --year 2026 --month 03 --input-dir "aifx\data\2026.03\charts"


# 3 dni

cd C:\rrudnick\wd3\aifx\tester-third
python3 process_candles.py --input-dir ../data/2025.01 --clean
python3 process_candles.py --input-dir ../data/2025.01 --mt --start-date 2025-01-01 --end-date 2025-01-03 --no-images


# test 5 charts
cd C:\rrudnick\wd3\aifx\strategy
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-00-00.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-00-15.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-00-30.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-00-45.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-01-00.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-01-15.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-01-30.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-01-45.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-02-00.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-02-15.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-02-30.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-02-45.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-03-00.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-03-15.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-03-30.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-03-45.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-04-00.csv

python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\25-01-02-08-00.csv

# case xxx
cd C:\rrudnick\wd3\aifx\strategy
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\26-02-17-03-45.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\26-02-17-04-00.csv
python3 .\magic_lines.py C:\rrudnick\wd3\aifx\strategy\test\26-02-17-04-15.csv