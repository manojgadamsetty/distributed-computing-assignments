#!/usr/bin/env bash
# Start commander and three lieutenants
python3 lieutenant.py --id 1 --config config.json > lt1.log 2>&1 &
sleep 0.3
python3 lieutenant.py --id 2 --config config.json > lt2.log 2>&1 &
sleep 0.3
python3 lieutenant.py --id 3 --config config.json > lt3.log 2>&1 &
sleep 0.3
python3 commander.py --config config.json --order ATTACK > cmd.log 2>&1 &
echo "Started commander and lieutenants. Logs: lt1.log lt2.log lt3.log cmd.log"
