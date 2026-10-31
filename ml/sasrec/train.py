"""python -m ml.sasrec.train  (requires torch and real activity sequences)."""
import random
import sys


def pad(seq, max_len):
    seq = seq[-max_len:]
    return [0] * (max_len - len(seq)) + seq


def main(seqs, item_ids, epochs=20, batch=32, max_len=20):
    import torch
    from ml.sasrec.model import SASRec

    usable = [s for s in seqs if len(s) >= 3]
    if len(usable) < 30:
        sys.exit(f"Only {len(usable)} usable user sequences: too few to train SASRec. Keep collecting activity.")
    model = SASRec(len(item_ids), max_len)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    n = len(item_ids)
    for ep in range(epochs):
        random.shuffle(usable)
        for i in range(0, len(usable), batch):
            rows = [[item_ids[s] for s in seq] for seq in usable[i:i + batch]]
            x = torch.tensor([pad(r[:-1], max_len) for r in rows])
            pos = torch.tensor([pad(r[1:], max_len) for r in rows])
            neg = torch.randint(1, n + 1, pos.shape) * (pos != 0)
            loss = model(x, pos, neg)
            opt.zero_grad(); loss.backward(); opt.step()
        print(f"epoch {ep + 1}: loss {loss.item():.4f}")
    return model
