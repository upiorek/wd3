#!/bin/bash

python3 ./create_month_folders.py --cleanup

python3 ./create_month_folders.py
python3 ./divide_us100_by_month.py
python3 ./divide_monthly_to_individual.py
