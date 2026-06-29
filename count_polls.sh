#!/bin/bash
for d in /home/softverse/hostedmt-diagnostics/*/; do
  count=$(ls -1 "${d}"screen-poll-*.png 2>/dev/null | wc -l)
  echo "$(basename "${d}") : ${count} images"
done
