#!/usr/bin/env bash

echo "Starting test" > slow_process.out
for i in $(seq 1 3)
do
    echo $i
    echo $i >> slow_process.out
    sleep 1
done

