#!/usr/bin/env bash

curl -H 'Accept: application/json' -X PUT --data-binary "@forwarding_tables.json" sdn-controller.local:8080/set_tables
