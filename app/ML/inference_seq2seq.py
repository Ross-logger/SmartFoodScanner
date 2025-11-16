"""
Inference for Seq2Seq OCR Correction Model
Good balance of accuracy and speed
"""

import torch
import torch.nn as nn
from pathlib import Path
from typing import List, Dict, Tuple


# Import model classes from training script
# (In production, these would be in a separate models.py file)
class CharVocab:
    """Character vocabulary for encoding/decoding"""
    
    def __init__(self):
        self.char2idx = {'<PAD>': 0, '<SOS>': 1, '<EOS>': 2, '<UNK>': 3}
        self.idx2char = {0: '<PAD>', 1: '<SOS>', 2: '<EOS>', 3: '<UNK>'}
    
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


class Encoder(nn.Module):
    """LSTM Encoder"""
    
    def __init__(self, vocab_size: int, embed_dim: int, hidden_dim: int, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        embedded = self.dropout(self.embedding(x))
        outputs, (hidden, cell) = self.lstm(embedded)
        return outputs, hidden, cell


class Attention(nn.Module):
    """Attention mechanism"""
    
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Linear(hidden_dim * 3, hidden_dim)
        self.v = nn.Linear(hidden_dim, 1, bias=False)
    
    def forward(self, hidden, encoder_outputs):
        batch_size = encoder_outputs.shape[0]
        src_len = encoder_outputs.shape[1]
        
        hidden = hidden.unsqueeze(1).repeat(1, src_len, 1)
        energy = torch.tanh(self.attn(torch.cat((hidden, encoder_outputs), dim=2)))
        attention = self.v(energy).squeeze(2)
        
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
        embedded = self.dropout(self.embedding(x))
        attn_weights = self.attention(hidden[-1], encoder_outputs)
        attn_weights = attn_weights.unsqueeze(1)
        context = torch.bmm(attn_weights, encoder_outputs)
        lstm_input = torch.cat((embedded, context), dim=2)
        output, (hidden, cell) = self.lstm(lstm_input, (hidden, cell))
        prediction = self.fc(output.squeeze(1))
        
        return prediction, hidden, cell


class Seq2SeqModel(nn.Module):
    """Sequence-to-Sequence Model"""
    
    def __init__(self, vocab: CharVocab, embed_dim: int = 128, hidden_dim: int = 256, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.vocab = vocab
        vocab_size = len(vocab)
        
        self.encoder = Encoder(vocab_size, embed_dim, hidden_dim, num_layers, dropout)
        self.decoder = Decoder(vocab_size, embed_dim, hidden_dim, num_layers, dropout)
        
        self.bridge_h = nn.Linear(hidden_dim * 2, hidden_dim)
        self.bridge_c = nn.Linear(hidden_dim * 2, hidden_dim)
    
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
                
                if (top1 == self.vocab.char2idx['<EOS>']).all():
                    break
            
            return torch.stack(predictions, dim=1)


class OcrCorrectorSeq2Seq:
    """
    Seq2Seq OCR Corrector for inference
    
    Usage:
        corrector = OcrCorrectorSeq2Seq()
        corrected = corrector.correct("s0y lec1th1n")
        # Returns: "soy lecithin"
    """
    
    def __init__(self, model_dir: str = "models/seq2seq", device: str = None):
        """
        Initialize Seq2Seq corrector
        
        Args:
            model_dir: Path to trained model directory
            device: Device to use (cuda/cpu)
        """
        self.model_dir = Path(model_dir)
        
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Load model
        if self.model_dir.exists():
            self._load_model()
        else:
            print(f"Warning: Model directory {model_dir} not found.")
            print("Run train_seq2seq.py first to train the model.")
            self.model = None
    
    def _load_model(self):
        """Load trained model"""
        model_path = self.model_dir / "best_model.pt"
        
        if not model_path.exists():
            print(f"Model file not found: {model_path}")
            self.model = None
            return
        
        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Extract vocab and config
        self.vocab = checkpoint['vocab']
        config = checkpoint['config']
        
        # Create model
        self.model = Seq2SeqModel(
            self.vocab,
            embed_dim=config['embed_dim'],
            hidden_dim=config['hidden_dim'],
            num_layers=config['num_layers'],
            dropout=config['dropout']
        )
        
        # Load weights
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()
        
        print(f"Model loaded from {model_path}")
    
    def correct(self, text: str, max_len: int = 100) -> str:
        """
        Correct OCR errors in text
        
        Args:
            text: Noisy text to correct
            max_len: Maximum output length
            
        Returns:
            Corrected text
        """
        if not text or self.model is None:
            return text
        
        # Encode input
        src = torch.tensor([self.vocab.encode(text.lower())]).to(self.device)
        
        # Predict
        with torch.no_grad():
            pred_indices = self.model.predict(src, max_len=max_len)[0].cpu().numpy()
        
        # Decode
        corrected = self.vocab.decode(pred_indices)
        
        return corrected
    
    def correct_batch(self, texts: List[str], max_len: int = 100) -> List[str]:
        """
        Correct multiple texts
        
        Args:
            texts: List of noisy texts
            max_len: Maximum output length
            
        Returns:
            List of corrected texts
        """
        if not texts or self.model is None:
            return texts
        
        # Encode all inputs
        max_input_len = max(len(t) for t in texts)
        src_batch = []
        for text in texts:
            src = self.vocab.encode(text.lower(), max_len=max_input_len)
            src_batch.append(src)
        
        src_tensor = torch.tensor(src_batch).to(self.device)
        
        # Predict
        with torch.no_grad():
            pred_batch = self.model.predict(src_tensor, max_len=max_len).cpu().numpy()
        
        # Decode all
        corrected_texts = []
        for pred_indices in pred_batch:
            corrected = self.vocab.decode(pred_indices)
            corrected_texts.append(corrected)
        
        return corrected_texts
    
    def correct_with_details(self, text: str, max_len: int = 100) -> Dict:
        """
        Correct text and return detailed information
        
        Args:
            text: Noisy text
            max_len: Maximum output length
            
        Returns:
            Dict with corrected text and details
        """
        corrected = self.correct(text, max_len)
        
        return {
            'original': text,
            'corrected': corrected,
            'model': 'seq2seq',
            'changed': corrected.lower() != text.lower()
        }


def demo():
    """Demo of the Seq2Seq OCR corrector"""
    print("="*60)
    print("Seq2Seq OCR Corrector - Demo")
    print("="*60)
    
    corrector = OcrCorrectorSeq2Seq()
    
    if corrector.model is None:
        print("\nModel not found. Please train the model first:")
        print("  python train_seq2seq.py")
        return
    
    # Test examples
    test_cases = [
        "s0y lec1th1n",
        "whey pr0te1n",
        "m0n0s0d1um glUtamate",
        "natral flvors",
        "c0rn syrup",
        "v1tam1n c",
        "sod1um benzoate",
        "art1f1c1al fl4vors",
        "palm o1l",
        "h1gh fruct0se c0rn syrup"
    ]
    
    print("\nTest Cases:")
    print("-"*60)
    
    for noisy in test_cases:
        result = corrector.correct_with_details(noisy)
        
        print(f"\nOriginal:  {result['original']}")
        print(f"Corrected: {result['corrected']}")
        print(f"Changed:   {result['changed']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    demo()

