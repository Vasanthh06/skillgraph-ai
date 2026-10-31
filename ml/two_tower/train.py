"""python -m ml.two_tower.train  (requires torch and real interaction data)."""
import random
import sys

from ml.two_tower.model import TwoTower  # noqa: F401  (import check)


def main(pairs, known_by_user, role_by_user, skill_ids, role_ids, epochs=10, batch=64):
    import torch

    if len(pairs) < 200:
        sys.exit(f"Only {len(pairs)} interactions: too few to train a meaningful model. Collect more activity first.")
    model = TwoTower(len(skill_ids), len(role_ids))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for ep in range(epochs):
        random.shuffle(pairs)
        for i in range(0, len(pairs) - batch + 1, batch):
            chunk = pairs[i:i + batch]
            L = 30
            known = torch.tensor([[skill_ids[s] for s in (known_by_user[u] - {p})][:L] + [0] * max(0, L - len(known_by_user[u] - {p})) for u, p in chunk])
            role = torch.tensor([role_ids.get(role_by_user.get(u), 0) for u, _ in chunk])
            pos = torch.tensor([skill_ids[p] for _, p in chunk])
            loss = model(known, role, pos)
            opt.zero_grad(); loss.backward(); opt.step()
        print(f"epoch {ep + 1}: loss {loss.item():.4f}")
    return model
