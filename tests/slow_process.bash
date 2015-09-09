#!/usr/bin/env bash

echo "Starting test" > outputfile.out
for i in $(seq 1 10)
do
    echo $i
    echo $i >> outputfile.out
    sleep 2
done

