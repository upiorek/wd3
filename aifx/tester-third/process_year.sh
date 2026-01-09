

for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
    python3 process_candles.py --input-dir ../data/2025.${month} --mt &
done

# wait for all background processes to finish
wait
echo "All months processed."

# Create temp directory
mkdir -p temp_year

# Copy result and decision files from each month
for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
    if [ -d "../data/2025.${month}/charts" ]; then
        cp ../data/2025.${month}/charts/*_result.txt temp_year/ 2>/dev/null || true
        cp ../data/2025.${month}/charts/*_decision.txt temp_year/ 2>/dev/null || true
    fi
done

# Zip the temp directory
zip -r wd_tester_$(date +%Y%m%d_%H%M%S).zip temp_year/

# Delete temp directory
rm -rf temp_year
