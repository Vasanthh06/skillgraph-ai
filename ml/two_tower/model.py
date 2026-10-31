"""Two-tower candidate generator (PyTorch). NOT trained and NOT run in this repo's tests.

User tower: mean of embeddings of the user's known skills + a target-role embedding.
Item tower: skill embedding (optionally initialised from the text embeddings in ml/embeddings).
Score = cosine(user, item); trained with in-batch sampled softmax.
Needs real (user, skill) interaction data: see preprocessing/build_dataset.user_skill_pairs.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class TwoTower(nn.Module):
    def __init__(self, n_skills: int, n_roles: int, dim: int = 64):
        super().__init__()
        self.skill_emb = nn.Embedding(n_skills + 1, dim, padding_idx=0)
        self.role_emb = nn.Embedding(n_roles + 1, dim, padding_idx=0)
        self.user_mlp = nn.Sequential(nn.Linear(2 * dim, dim), nn.ReLU(), nn.Linear(dim, dim))
        self.item_mlp = nn.Sequential(nn.Linear(dim, dim), nn.ReLU(), nn.Linear(dim, dim))

    def user_vec(self, known: torch.Tensor, role: torch.Tensor) -> torch.Tensor:
        """known: (B, L) skill ids, 0 = padding. role: (B,)."""
        mask = (known != 0).unsqueeze(-1).float()
        pooled = (self.skill_emb(known) * mask).sum(1) / mask.sum(1).clamp(min=1.0)
        return F.normalize(self.user_mlp(torch.cat([pooled, self.role_emb(role)], dim=-1)), dim=-1)

    def item_vec(self, items: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.item_mlp(self.skill_emb(items)), dim=-1)

    def forward(self, known, role, pos_items, temperature: float = 0.07):
        u, v = self.user_vec(known, role), self.item_vec(pos_items)
        logits = u @ v.T / temperature          # in-batch negatives
        return F.cross_entropy(logits, torch.arange(len(u), device=logits.device))
