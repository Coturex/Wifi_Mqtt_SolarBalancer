#!/bin/bash
ts=`/bin/date +%Y%m%d%H%M`
mv prod archives/$ts
mkdir prod
cp *py prod
mv prod/regulation.py prod/regulation_prod.py
cp archives/$ts/*.ini prod
cp archives/$ts/*.log prod
cp calibration/power_calibration_ECS.csv prod
