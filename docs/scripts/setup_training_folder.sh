#!/bin/bash
mkdir -p training_data/{raw,processed/{train,val,test},replay_buffer,promoted,versions,synthetic}
echo "=== Massive Training Folder Created ==="
echo "Put your .csv / .mat files in training_data/raw/"
echo "Run this script again anytime to recreate structure."
