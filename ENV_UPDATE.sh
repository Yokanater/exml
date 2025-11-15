#!/bin/bash

if [ ! -d ".git" ]; then
    echo "Run this script from the root of a git repository."
    exit 1
fi

echo "[*] Enabling sparse checkout..."
git sparse-checkout init --cone

echo "[*] Setting sparse-checkout rules..."
echo "/*" > .git/info/sparse-checkout
echo "!/models/" >> .git/info/sparse-checkout

echo "[*] Fetching latest commits..."
git fetch

echo "[*] Hard resetting..."
git reset --hard origin/main

echo "[*] Environment updated successfully!"
