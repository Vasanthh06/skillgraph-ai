"""SASRec: self-attentive sequential recommendation (Kang & McAuley, 2018), PyTorch. NOT trained here.

Predicts the next skill a user will engage with from the ordered sequence of skills they searched/viewed/
completed. Causal self-attention over item embeddings plus learned positions.
"""
import torch
import torch.nn as nn


class SASRec(nn.Module):
    def __init__(self, n_items: int, max_len: int = 20, dim: int = 64, heads: int = 2, layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.max_len = max_len
        self.item_emb = nn.Embedding(n_items + 1, dim, padding_idx=0)
        self.pos_emb = nn.Embedding(max_len, dim)
        block = nn.TransformerEncoderLayer(dim, heads, dim * 4, dropout, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(block, layers)
        self.norm = nn.LayerNorm(dim)
        self.drop = nn.Dropout(dropout)

    def encode(self, seq: torch.Tensor) -> torch.Tensor:
        """seq: (B, L) item ids, 0 = left padding. Returns (B, L, dim)."""
        B, L = seq.shape
        x = self.item_emb(seq) * (self.item_emb.embedding_dim ** 0.5) + self.pos_emb(torch.arange(L, device=seq.device))
        causal = torch.triu(torch.ones(L, L, dtype=torch.bool, device=seq.device), diagonal=1)
        h = self.encoder(self.drop(x), mask=causal, src_key_padding_mask=(seq == 0))
        return self.norm(h)

    def forward(self, seq, pos, neg):
        """Binary cross-entropy with one sampled negative per position (as in the paper)."""
        h = self.encode(seq)
        ps, ns = (h * self.item_emb(pos)).sum(-1), (h * self.item_emb(neg)).sum(-1)
        mask = (pos != 0).float()
        bce = nn.functional.binary_cross_entropy_with_logits
        return ((bce(ps, torch.ones_like(ps), reduction="none") + bce(ns, torch.zeros_like(ns), reduction="none")) * mask).sum() / mask.sum().clamp(min=1)

    @torch.no_grad()
    def predict(self, seq: torch.Tensor, k: int = 5) -> torch.Tensor:
        h = self.encode(seq)[:, -1]
        scores = h @ self.item_emb.weight.T
        scores[:, 0] = float("-inf")
        return scores.topk(k, dim=-1).indices
