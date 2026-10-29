#!/bin/bash
# Print the launchable module names (imports2/*.py without the .py), one per
# line, sorted.  Support files that are not pentest modules are excluded.
find /opt/SKELETON/imports2 -maxdepth 1 -name '*.py' -printf '%f\n' \
  | sed 's/\.py$//' \
  | grep -vxE 'template|glossary|terminal_osin|config' \
  | sort
