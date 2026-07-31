#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
for script in $DIR/test*.sh $DIR/register*.sh $DIR/query*.sh; do bash "$script"; done
echo 'PoC 04 done.'\n