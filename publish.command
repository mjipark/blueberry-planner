#!/bin/bash
# Double-click to publish Blueberry Planner to GitHub Pages.
cd "$(dirname "$0")" || exit 1
echo "Publishing Blueberry Planner…"
git add -A
git commit -m "Update Blueberry Planner" || echo "(nothing new to commit)"
if git push origin main; then
  echo; echo "✅ Pushed. GitHub Pages updates in about a minute: https://mjipark.github.io/blueberry-planner/"
else
  echo; echo "❌ Push failed — see the message above."
fi
echo; read -n 1 -s -r -p "Press any key to close."
