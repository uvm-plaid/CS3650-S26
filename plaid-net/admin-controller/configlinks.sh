#!/usr/bin/env bash

curl -H 'Accept: application/json' -X PUT -d '{"connected" : [ [1,5] , [5,9] ]}' http://sdn-controller.local:8080/configlinks
