#!/usr/bin/env python
import argparse, json, math, os
import numpy as np
import torch
from torch.utils.data import DataLoader
from datasets import load_dataset
from transformers import (AutoModelForMaskedLM, AutoTokenizer, DataCollatorForLanguageModeling,
                          Trainer, TrainingArguments, default_data_collator)

class EWCTrainer(Trainer):
    def __init__(self, fisher_dict=None, ewc_lambda=0.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fisher = fisher_dict or {}
        self.ewc_lambda = ewc_lambda
        self._param_names = [n for n, p in self.model.named_parameters() if p.requires_grad]
        self._theta_star = {n: p.detach().clone() for n, p in self.model.named_parameters() if p.requires_grad}

    def compute_loss(self, model, inputs, return_outputs=False):
        outputs = model(**inputs)
        loss = outputs.loss
        if self.fisher and self.ewc_lambda > 0:
            penalty = 0.0
            for n, p in model.named_parameters():
                if n in self.fisher:
                    fisher = self.fisher[n]
                    theta0 = self._theta_star[n]
                    penalty = penalty + (fisher * (p - theta0) ** 2).sum()
            loss = loss + (self.ewc_lambda / 2.0) * penalty
        return (loss, outputs) if return_outputs else loss

def estimate_fisher(model, dataloader, device, max_samples):
    model.eval()
    grads2 = {}
    n = 0
    for batch in dataloader:
        if n >= max_samples: break
        batch = {k: v.to(device) for k, v in batch.items()}
        model.zero_grad()
        out = model(**batch)
        out.loss.backward()
        for name, p in model.named_parameters():
            if p.grad is None or not p.requires_grad:
                continue
            g2 = p.grad.detach() ** 2
            if name not in grads2:
                grads2[name] = g2.clone()
            else:
                grads2[name] += g2
        n += 1
    for k in grads2:
        grads2[k] /= max(1, n)
    return {k: v.detach() for k, v in grads2.items()}

def prepare_dataset(train_file, tokenizer, seq_len):
    ds = load_dataset("text", data_files={"train": train_file})
    def tok(ex):
        return tokenizer(ex["text"], truncation=True, max_length=seq_len)
    tokenized = ds.map(tok, batched=True, remove_columns=["text"])
    return tokenized

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model_path', required=True)
    ap.add_argument('--train_file', required=True)
    ap.add_argument('--fisher_samples', type=int, default=4096)
    ap.add_argument('--fisher_out', required=True)
    ap.add_argument('--ewc_lambda', type=float, default=5.0)
    ap.add_argument('--epochs', type=int, default=1)
    ap.add_argument('--seq_len', type=int, default=512)
    ap.add_argument('--batch_size', type=int, default=8)
    ap.add_argument('--lr', type=float, default=2e-4)
    ap.add_argument('--output_dir', required=True)
    args = ap.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = AutoModelForMaskedLM.from_pretrained(args.model_path)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path)

    # Dataset and dataloader for Fisher
    ds = prepare_dataset(args.train_file, tokenizer, args.seq_len)
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=True)
    dl = DataLoader(ds['train'], batch_size=args.batch_size, shuffle=True, collate_fn=collator)

    # Fisher estimation
    fisher = estimate_fisher(model.to(device), dl, device, max_samples=args.fisher_samples)
    # Save
    torch.save({k: v.cpu() for k, v in fisher.items()}, args.fisher_out)

    # Fine-tune with EWC
    model = AutoModelForMaskedLM.from_pretrained(args.model_path)
    tokenized = ds  # reuse
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        logging_steps=50,
        save_steps=500,
        report_to=["none"],
        bf16=torch.cuda.is_available(),
    )
    fisher_cpu = torch.load(args.fisher_out)
    trainer = EWCTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized['train'],
        data_collator=collator,
        fisher_dict=fisher_cpu,
        ewc_lambda=args.ewc_lambda,
    )
    trainer.train()
    trainer.save_model(args.output_dir)

if __name__ == '__main__':
    main()