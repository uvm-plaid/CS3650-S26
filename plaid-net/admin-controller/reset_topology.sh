#!/usr/bin/env bash

curl -H 'Accept: application/json' -X GET sdn-controller.local:8080/reset_topology
