#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
for script in $DIR/test*.sh $DIR/create*.sh $DIR/validate*.sh; do bash "$script"; done
echo 'PoC 05 done.'\n