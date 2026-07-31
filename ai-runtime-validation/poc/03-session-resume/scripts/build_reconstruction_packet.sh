#!/bin/bash
# scripts/build_reconstruction_packet.sh
TYPE=$1

if [ "$TYPE" == "root" ]; then
  cat ../fixtures/root_reconstruction_packet.json
elif [ "$TYPE" == "feature" ]; then
  cat ../fixtures/feature_reconstruction_packet.json
else
  echo "Unknown type"
  exit 1
fi
