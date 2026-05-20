#!/bin/bash

kill $(ps aux | grep '[o]vs' | awk '{print $2}')
