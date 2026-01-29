"""
Transformer-based OCR Correction using T5
Highest accuracy, requires GPU for training
Can use Google Colab free tier
"""

import os
from pathlib import Path
from typing import List, Tuple
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForSeq2Seq
)
from tqdm import tqdm
import json


class OCRCorrectionDataset(Dataset):
    """Dataset for T5 OCR correction"""
    
    def __init__(self, pairs: List[Tuple[str, str]], tokenizer, max_length: int = 128):
        self.pairs = pairs
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx):
        noisy, clean = self.pairs[idx]
        
        # Add task prefix for T5
        input_text = f"correct ocr: {noisy}"
        target_text = clean
        
        # Tokenize
        input_encoding = self.tokenizer(
            input_text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        target_encoding = self.tokenizer(
            target_text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        labels = target_encoding['input_ids'].squeeze()
        # Replace padding token id's with -100 so they are ignored by loss
        labels[labels == self.tokenizer.pad_token_id] = -100
        
        return {
            'input_ids': input_encoding['input_ids'].squeeze(),
            'attention_mask': input_encoding['attention_mask'].squeeze(),
            'labels': labels
        }


def train_transformer_model(
    train_file: str = "data/train_pairs.txt",
    test_file: str = "data/test_pairs.txt",
    output_dir: str = "models/transformer",
    model_name: str = "t5-small",  # or "google/byt5-small" for character-level
    batch_size: int = 16,
    num_epochs: int = 3,
    learning_rate: float = 5e-5,
    max_length: int = 128,
    device: str = None
):
    """
    Train T5-based OCR correction model
    
    Args:
        train_file: Path to training pairs
        test_file: Path to test pairs
        output_dir: Output directory
        model_name: HuggingFace model name (t5-small, t5-base, or google/byt5-small)
        batch_size: Training batch size
        num_epochs: Number of training epochs
        learning_rate: Learning rate
        max_length: Maximum sequence length
        device: Device to use (cuda/cpu)
    """
    
    print("="*60)
    print("Training Transformer OCR Correction Model")
    print("="*60)
    
    # Device
    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nUsing device: {device}")
    
    if device == 'cpu':
        print("\n⚠️  WARNING: Training on CPU will be very slow!")
        print("Consider using Google Colab with GPU for faster training.")
        print("Colab notebook: https://colab.research.google.com/")
    
    # Load data
    print("\nLoading training data...")
    train_pairs = []
    with open(train_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '\t' in line:
                noisy, clean = line.strip().split('\t')
                train_pairs.append((noisy, clean))
    print(f"Loaded {len(train_pairs)} training pairs")
    
    print("\nLoading test data...")
    test_pairs = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '\t' in line:
                noisy, clean = line.strip().split('\t')
                test_pairs.append((noisy, clean))
    print(f"Loaded {len(test_pairs)} test pairs")
    
    # Load model and tokenizer
    print(f"\nLoading {model_name} model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,}")
    
    # Create datasets
    print("\nPreparing datasets...")
    train_dataset = OCRCorrectionDataset(train_pairs, tokenizer, max_length)
    test_dataset = OCRCorrectionDataset(test_pairs, tokenizer, max_length)
    
    # Data collator
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        logging_dir=f'{output_dir}/logs',
        logging_steps=100,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        save_total_limit=2,
        fp16=device == 'cuda',  # Use mixed precision on GPU
        report_to='none',  # Disable wandb/tensorboard
        push_to_hub=False,
    )
    
    # Trainer
    print("\nInitializing trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        data_collator=data_collator,
    )
    
    # Train
    print("\n" + "="*60)
    print("Training...")
    print("="*60)
    
    trainer.train()
    
    # Save model
    print("\nSaving model...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Save config
    config = {
        'model_name': model_name,
        'max_length': max_length,
        'model_type': 'transformer'
    }
    with open(f"{output_dir}/config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    # Evaluation
    print("\n" + "="*60)
    print("Evaluation:")
    print("="*60)
    
    model.eval()
    device_obj = torch.device(device)
    model.to(device_obj)
    
    correct = 0
    total = min(100, len(test_pairs))
    examples = []
    
    print("\nGenerating predictions...")
    for i in tqdm(range(total)):
        noisy, clean = test_pairs[i]
        
        input_text = f"correct ocr: {noisy}"
        input_ids = tokenizer(input_text, return_tensors='pt').input_ids.to(device_obj)
        
        with torch.no_grad():
            outputs = model.generate(
                input_ids,
                max_length=max_length,
                num_beams=4,
                early_stopping=True
            )
        
        predicted = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        is_correct = predicted.strip().lower() == clean.lower()
        if is_correct:
            correct += 1
        
        if len(examples) < 20:
            examples.append((noisy, clean, predicted, is_correct))
    
    accuracy = correct / total * 100
    print(f"\nAccuracy: {accuracy:.2f}% ({correct}/{total})")
    
    print("\n" + "="*60)
    print("Example Predictions:")
    print("="*60)
    for noisy, clean, predicted, is_correct in examples[:10]:
        status = "✓" if is_correct else "✗"
        print(f"{status} Noisy: {noisy:30s} → Pred: {predicted:30s} (Truth: {clean})")
    
    print("\n" + "="*60)
    print("Training complete!")
    print("="*60)
    print(f"Model saved to: {output_dir}")
    print(f"Accuracy: {accuracy:.2f}%")
    
    return model, tokenizer


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Transformer OCR correction model")
    parser.add_argument("--train", default="data/train_pairs.txt", help="Training pairs file")
    parser.add_argument("--test", default="data/test_pairs.txt", help="Test pairs file")
    parser.add_argument("--output", default="models/transformer", help="Output directory")
    parser.add_argument("--model", default="t5-small", help="Model name (t5-small, t5-base, google/byt5-small)")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--max-length", type=int, default=128, help="Max sequence length")
    parser.add_argument("--device", type=str, default=None, help="Device (cuda/cpu)")
    
    args = parser.parse_args()
    
    train_transformer_model(
        train_file=args.train,
        test_file=args.test,
        output_dir=args.output,
        model_name=args.model,
        batch_size=args.batch_size,
        num_epochs=args.epochs,
        learning_rate=args.lr,
        max_length=args.max_length,
        device=args.device
    )


if __name__ == "__main__":
    main()

