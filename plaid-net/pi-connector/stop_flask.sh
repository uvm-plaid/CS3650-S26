#!/bin/bash

kill $(ps aux | grep '[f]lask' | awk '{print $2}')
