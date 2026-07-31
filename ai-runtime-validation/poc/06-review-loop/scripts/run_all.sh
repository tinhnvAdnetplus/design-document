#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
for script in $DIR/test*.sh $DIR/simulate*.sh; do bash "$script"; done
echo 'PoC 06 done.'\n