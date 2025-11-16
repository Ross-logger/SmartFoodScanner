"""
Sequence-to-Sequence OCR Correction Model
Character-level encoder-decoder with attention
Good balance of accuracy and efficiency
"""

import os
import json
import pickle
from pathlib import Path
from typing import List, Tuple, Dict
import random

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm


class CharVocab:
    """Character vocabulary for encoding/decoding"""
    
    def __init__(self):
        self.char2idx = {'<PAD>': 0, '<SOS>': 1, '<EOS>': 2, '<UNK>': 3}
        self.idx2char = {0: '<PAD>', 1: '<SOS>', 2: '<EOS>', 3: '<UNK>'}
        self.char_count = {}
    
    def build_vocab(self, texts: List[str]):
        """Build vocabulary from texts"""
        for text in texts:
            for char in text:
                self.char_count[char] = self.char_count.get(char, 0) + 1
        
        # Add characters to vocab (sorted by frequency)
        idx = len(self.char2idx)
        for char, _ in sorted(self.char_count.items(), key=lambda x: -x[1]):
            if char not in self.char2idx:
                self.char2idx[char] = idx
                self.idx2char[idx] = char
                idx += 1
    
    def encode(self, text: str, max_len: int = None) -> List[int]:
        """Encode text to indices"""
        indices = [self.char2idx.get(c, self.char2idx['<UNK>']) for c in text]
        
        if max_len:
            if len(indices) < max_len:
                indices += [self.char2idx['<PAD>']] * (max_len - len(indices))
            else:
                indices = indices[:max_len]
        
        return indices
    
    def decode(self, indices: List[int]) -> str:
        """Decode indices to text"""
        chars = []
        for idx in indices:
            if idx == self.char2idx['<EOS>']:
                break
            if idx not in [self.char2idx['<PAD>'], self.char2idx['<SOS>'], self.char2idx['<UNK>']]:
                chars.append(self.idx2char.get(idx, ''))
        return ''.join(chars)
    
    def __len__(self):
        return len(self.char2idx)


class OCRDataset(Dataset):
    """Dataset for OCR correction pairs"""
    
    def __init__(self, pairs: List[Tuple[str, str]], vocab: CharVocab, max_len: int = 100):
        self.pairs = pairs
        self.vocab = vocab
        self.max_len = max_len
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx):
        noisy, clean = self.pairs[idx]
        
        # Encode
        src = self.vocab.encode(noisy, self.max_len)
        tgt = self.vocab.encode(clean, self.max_len)
        
        # Add SOS and EOS tokens to target
        tgt = [self.vocab.char2idx['<SOS>']] + tgt + [self.vocab.char2idx['<EOS>']]
        
        return torch.tensor(src), torch.tensor(tgt)


class Encoder(nn.Module):
    """LSTM Encoder"""
    
    def __init__(self, vocab_size: int, embed_dim: int, hidden_dim: int, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # x: (batch, seq_len)
        embedded = self.dropout(self.embedding(x))  # (batch, seq_len, embed_dim)
        outputs, (hidden, cell) = self.lstm(embedded)
        return outputs, hidden, cell


class Attention(nn.Module):
    """Attention mechanism"""
    
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Linear(hidden_dim * 3, hidden_dim)
        self.v = nn.Linear(hidden_dim, 1, bias=False)
    
    def forward(self, hidden, encoder_outputs):
        # hidden: (batch, hidden_dim)
        # encoder_outputs: (batch, src_len, hidden_dim * 2)
        
        batch_size = encoder_outputs.shape[0]
        src_len = encoder_outputs.shape[1]
        
        # Repeat hidden state src_len times
        hidden = hidden.unsqueeze(1).repeat(1, src_len, 1)  # (batch, src_len, hidden_dim)
        
        # Concatenate
        energy = torch.tanh(self.attn(torch.cat((hidden, encoder_outputs), dim=2)))
        attention = self.v(energy).squeeze(2)  # (batch, src_len)
        
        return torch.softmax(attention, dim=1)


class Decoder(nn.Module):
    """LSTM Decoder with Attention"""
    
    def __init__(self, vocab_size: int, embed_dim: int, hidden_dim: int, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.attention = Attention(hidden_dim)
        self.lstm = nn.LSTM(embed_dim + hidden_dim * 2, hidden_dim, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_dim, vocab_size)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, hidden, cell, encoder_outputs):
        # x: (batch, 1)
        # hidden: (num_layers * 2, batch, hidden_dim)
        # encoder_outputs: (batch, src_len, hidden_dim * 2)
        
        embedded = self.dropout(self.embedding(x))  # (batch, 1, embed_dim)
        
        # Get attention weights
        attn_weights = self.attention(hidden[-1], encoder_outputs)  # (batch, src_len)
        attn_weights = attn_weights.unsqueeze(1)  # (batch, 1, src_len)
        
        # Apply attention
        context = torch.bmm(attn_weights, encoder_outputs)  # (batch, 1, hidden_dim * 2)
        
        # Concatenate embedding and context
        lstm_input = torch.cat((embedded, context), dim=2)  # (batch, 1, embed_dim + hidden_dim * 2)
        
        # LSTM
        output, (hidden, cell) = self.lstm(lstm_input, (hidden, cell))
        
        # Prediction
        prediction = self.fc(output.squeeze(1))  # (batch, vocab_size)
        
        return prediction, hidden, cell


class Seq2SeqModel(nn.Module):
    """Sequence-to-Sequence Model"""
    
    def __init__(self, vocab: CharVocab, embed_dim: int = 128, hidden_dim: int = 256, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.vocab = vocab
        vocab_size = len(vocab)
        
        self.encoder = Encoder(vocab_size, embed_dim, hidden_dim, num_layers, dropout)
        self.decoder = Decoder(vocab_size, embed_dim, hidden_dim, num_layers, dropout)
        
        # Bridge to connect bidirectional encoder to decoder
        self.bridge_h = nn.Linear(hidden_dim * 2, hidden_dim)
        self.bridge_c = nn.Linear(hidden_dim * 2, hidden_dim)
    
    def forward(self, src, tgt, teacher_forcing_ratio: float = 0.5):
        # src: (batch, src_len)
        # tgt: (batch, tgt_len)
        
        batch_size = src.shape[0]
        tgt_len = tgt.shape[1]
        vocab_size = self.decoder.vocab_size
        
        # Encoder
        encoder_outputs, hidden, cell = self.encoder(src)
        
        # Bridge: combine bidirectional hidden states
        # hidden: (num_layers * 2, batch, hidden_dim) -> (num_layers, batch, hidden_dim * 2)
        hidden = hidden.view(-1, 2, batch_size, hidden.shape[2])  # (num_layers, 2, batch, hidden_dim)
        hidden = hidden.permute(0, 2, 1, 3).contiguous()  # (num_layers, batch, 2, hidden_dim)
        hidden = hidden.view(-1, batch_size, hidden.shape[2] * 2)  # (num_layers, batch, hidden_dim * 2)
        hidden = torch.tanh(self.bridge_h(hidden))  # (num_layers, batch, hidden_dim)
        
        cell = cell.view(-1, 2, batch_size, cell.shape[2])
        cell = cell.permute(0, 2, 1, 3).contiguous()
        cell = cell.view(-1, batch_size, cell.shape[2] * 2)
        cell = torch.tanh(self.bridge_c(cell))
        
        # Decoder
        outputs = torch.zeros(batch_size, tgt_len, vocab_size).to(src.device)
        input_token = tgt[:, 0].unsqueeze(1)  # <SOS> token
        
        for t in range(1, tgt_len):
            output, hidden, cell = self.decoder(input_token, hidden, cell, encoder_outputs)
            outputs[:, t] = output
            
            # Teacher forcing
            teacher_force = random.random() < teacher_forcing_ratio
            top1 = output.argmax(1).unsqueeze(1)
            input_token = tgt[:, t].unsqueeze(1) if teacher_force else top1
        
        return outputs
    
    def predict(self, src, max_len: int = 100):
        """Predict without teacher forcing"""
        self.eval()
        with torch.no_grad():
            batch_size = src.shape[0]
            
            # Encoder
            encoder_outputs, hidden, cell = self.encoder(src)
            
            # Bridge
            hidden = hidden.view(-1, 2, batch_size, hidden.shape[2])
            hidden = hidden.permute(0, 2, 1, 3).contiguous()
            hidden = hidden.view(-1, batch_size, hidden.shape[2] * 2)
            hidden = torch.tanh(self.bridge_h(hidden))
            
            cell = cell.view(-1, 2, batch_size, cell.shape[2])
            cell = cell.permute(0, 2, 1, 3).contiguous()
            cell = cell.view(-1, batch_size, cell.shape[2] * 2)
            cell = torch.tanh(self.bridge_c(cell))
            
            # Decoder
            input_token = torch.full((batch_size, 1), self.vocab.char2idx['<SOS>'], dtype=torch.long).to(src.device)
            predictions = []
            
            for _ in range(max_len):
                output, hidden, cell = self.decoder(input_token, hidden, cell, encoder_outputs)
                top1 = output.argmax(1)
                predictions.append(top1)
                input_token = top1.unsqueeze(1)
                
                # Check if all sequences have generated <EOS>
                if (top1 == self.vocab.char2idx['<EOS>']).all():
                    break
            
            return torch.stack(predictions, dim=1)  # (batch, pred_len)


def train_seq2seq_model(
    train_file: str = "data/train_pairs.txt",
    test_file: str = "data/test_pairs.txt",
    output_dir: str = "models/seq2seq",
    embed_dim: int = 128,
    hidden_dim: int = 256,
    num_layers: int = 2,
    dropout: float = 0.3,
    batch_size: int = 64,
    num_epochs: int = 20,
    learning_rate: float = 0.001,
    device: str = None
):
    """Train Seq2Seq model"""
    
    print("="*60)
    print("Training Seq2Seq OCR Correction Model")
    print("="*60)
    
    # Device
    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nUsing device: {device}")
    
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
    
    # Build vocabulary
    print("\nBuilding vocabulary...")
    vocab = CharVocab()
    all_texts = [pair[0] for pair in train_pairs] + [pair[1] for pair in train_pairs]
    vocab.build_vocab(all_texts)
    print(f"Vocabulary size: {len(vocab)}")
    
    # Create datasets
    train_dataset = OCRDataset(train_pairs, vocab)
    test_dataset = OCRDataset(test_pairs, vocab)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    # Create model
    print("\nCreating model...")
    model = Seq2SeqModel(vocab, embed_dim, hidden_dim, num_layers, dropout).to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,}")
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss(ignore_index=vocab.char2idx['<PAD>'])
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=2, factor=0.5)
    
    # Training loop
    print("\n" + "="*60)
    print("Training...")
    print("="*60)
    
    best_loss = float('inf')
    
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}")
        for src, tgt in progress_bar:
            src, tgt = src.to(device), tgt.to(device)
            
            optimizer.zero_grad()
            
            # Forward
            output = model(src, tgt)
            
            # Calculate loss
            output = output[:, 1:].reshape(-1, output.shape[-1])
            tgt = tgt[:, 1:].reshape(-1)
            
            loss = criterion(output, tgt)
            
            # Backward
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            train_loss += loss.item()
            progress_bar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        train_loss /= len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for src, tgt in test_loader:
                src, tgt = src.to(device), tgt.to(device)
                output = model(src, tgt, teacher_forcing_ratio=0)
                
                output = output[:, 1:].reshape(-1, output.shape[-1])
                tgt = tgt[:, 1:].reshape(-1)
                
                loss = criterion(output, tgt)
                val_loss += loss.item()
        
        val_loss /= len(test_loader)
        scheduler.step(val_loss)
        
        print(f"\nEpoch {epoch+1}: Train Loss = {train_loss:.4f}, Val Loss = {val_loss:.4f}")
        
        # Save best model
        if val_loss < best_loss:
            best_loss = val_loss
            Path(output_dir).mkdir(exist_ok=True, parents=True)
            torch.save({
                'model_state_dict': model.state_dict(),
                'vocab': vocab,
                'config': {
                    'embed_dim': embed_dim,
                    'hidden_dim': hidden_dim,
                    'num_layers': num_layers,
                    'dropout': dropout
                }
            }, f"{output_dir}/best_model.pt")
            print(f"Saved best model (val_loss: {val_loss:.4f})")
    
    # Evaluate
    print("\n" + "="*60)
    print("Evaluation:")
    print("="*60)
    
    model.eval()
    correct = 0
    total = len(test_pairs)
    
    examples = []
    for i in range(min(20, total)):
        noisy, clean = test_pairs[i]
        src = torch.tensor([vocab.encode(noisy)]).to(device)
        pred_indices = model.predict(src, max_len=len(clean) + 10)[0].cpu().numpy()
        predicted = vocab.decode(pred_indices)
        
        is_correct = predicted == clean.lower()
        if is_correct:
            correct += 1
        
        examples.append((noisy, clean, predicted, is_correct))
    
    accuracy = correct / min(20, total) * 100
    print(f"\nSample Accuracy: {accuracy:.2f}%")
    
    print("\nExample predictions:")
    for noisy, clean, predicted, is_correct in examples[:10]:
        status = "✓" if is_correct else "✗"
        print(f"{status} Noisy: {noisy:30s} → Pred: {predicted:30s} (Truth: {clean})")
    
    print("\n" + "="*60)
    print("Training complete!")
    print("="*60)
    print(f"Model saved to: {output_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Seq2Seq OCR correction model")
    parser.add_argument("--train", default="data/train_pairs.txt", help="Training pairs file")
    parser.add_argument("--test", default="data/test_pairs.txt", help="Test pairs file")
    parser.add_argument("--output", default="models/seq2seq", help="Output directory")
    parser.add_argument("--embed-dim", type=int, default=128, help="Embedding dimension")
    parser.add_argument("--hidden-dim", type=int, default=256, help="Hidden dimension")
    parser.add_argument("--num-layers", type=int, default=2, help="Number of LSTM layers")
    parser.add_argument("--dropout", type=float, default=0.3, help="Dropout rate")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--epochs", type=int, default=20, help="Number of epochs")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--device", type=str, default=None, help="Device (cuda/cpu)")
    
    args = parser.parse_args()
    
    train_seq2seq_model(
        train_file=args.train,
        test_file=args.test,
        output_dir=args.output,
        embed_dim=args.embed_dim,
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        dropout=args.dropout,
        batch_size=args.batch_size,
        num_epochs=args.epochs,
        learning_rate=args.lr,
        device=args.device
    )


if __name__ == "__main__":
    main()

