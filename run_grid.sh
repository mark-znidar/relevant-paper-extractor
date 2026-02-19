#!/usr/bin/env zsh
# Runs build_prompt.py over a grid of parameters.
# Usage: zsh run_grid.sh

N_WORDS=(1000 2000 3000 4000 6000 8000 10000 20000)
PRIORITY_DATES=(2026-01-01 2025-10-01 2025-07-01)
CITATIONS=(10 8 6 4 2 1)

total=$(( ${#N_WORDS[@]} * ${#PRIORITY_DATES[@]} * ${#CITATIONS[@]} ))
count=0

for nw in "${N_WORDS[@]}"; do
  for pd in "${PRIORITY_DATES[@]}"; do
    for cit in "${CITATIONS[@]}"; do
      count=$(( count + 1 ))
      echo "[$count/$total] --n_words $nw --priority_date $pd --citations $cit"
      python build_prompt.py --n_words "$nw" --priority_date "$pd" --citations "$cit"
      echo ""
    done
  done
done

echo "Done. All $total combinations saved to paper_prompts/"
