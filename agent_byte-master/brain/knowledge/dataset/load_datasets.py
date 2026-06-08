#!/usr/bin/env python3
"""Load key NLP datasets for bot training"""
from datasets import load_dataset

# Sentiment Analysis
print("Loading Sentiment140...")
sent140 = load_dataset("sentiment140", split="train[:1000]")
print(f"  {len(sent140)} samples")

print("Loading IMDb...")
imdb = load_dataset("imdb", split="train[:1000]")
print(f"  {len(imdb)} samples")

# Q&A
print("Loading SQuAD...")
squad = load_dataset("squad", split="train[:500]")
print(f"  {len(squad)} samples")

# NER
print("Loading CoNLL-2003...")
conll = load_dataset("conll2003", split="train[:500]")
print(f"  {len(conll)} samples")

# Summarization
print("Loading CNN/DailyMail...")
cnn = load_dataset("cnn_dailymail", "3.0.0", split="train[:100]")
print(f"  {len(cnn)} samples")

# Dialogue
print("Loading Amazon Reviews...")
amazon = load_dataset("amazon_polarity", split="train[:1000]")
print(f"  {len(amazon)} samples")

print("\n✅ All datasets loaded!")
print("\nExample usage:")
print("  from datasets import load_dataset")
print("  ds = load_dataset('squad')")