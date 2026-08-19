

import torch
import torch.nn as nn
from torch.nn import functional as F
from tqdm import tqdm

# Hyperparameters
block_size = 16
batch_size = 64
max_iters = 10000
learning_rate = 1e-3
device = 'cuda' if torch.cuda.is_available() else 'cpu'


class BigramLanguageModel(nn.Module):

    def __init__(self,vocab_size):
        super().__init__()
        self.token_embedding_table = nn.Embedding(vocab_size,vocab_size)

    def forward(self,idx,targets=None):
        logits = self.token_embedding_table(idx)

        if targets is None:
            loss = None
        else:
            #Batch , time , size 
            B,T,C = logits.shape
            logits = logits.view(B*T,C)
            targets = targets.view(B*T)
            loss = F.cross_entropy(logits,targets)
        return logits, loss 
    
    def generate(self,idx,max_new_tokens):

        for _ in range(max_new_tokens):
            logits, _ = self(idx)

            logits = logits[:,-1,:]
            probs = F.softmax(logits,dim=-1)
            idx_next = torch.multinomial(probs,num_samples=1)
            idx = torch.cat((idx,idx_next),dim=1)
        return idx


def get_text():
    with open('./scraper/ims15_6_clean.txt','r',encoding='utf-8') as f:
        text = f.read()
        print("length of ds: ", len(text))
        chars = sorted(list(set(text)))
        print("characters: ",chars)
        return text,chars



def get_batch(block_size,batch_size,type='train'):
    data = train_data if type == 'train' else val_data
    ix = torch.randint(len(data) - block_size, (batch_size,))
    x = torch.stack([data[i:i+block_size] for i in ix])
    y = torch.stack([data[i+1:i+block_size+1] for i in ix])
    x,y = x.to(device),y.to(device)
    return x,y

text,chars = get_text()
stoi = {ch:i for i,ch in enumerate(chars)}
itos = {i:ch for i,ch in enumerate(chars)}
encode = lambda s: [stoi[c] for c in s]
decode = lambda c: [itos[i] for i in c]



data = torch.tensor(encode(text), dtype=torch.long)

n = int(0.9*len(data))

train_data = data[:n]
val_data = data[n:]



m = BigramLanguageModel(len(chars))
m.to(device)


optimizer = torch.optim.AdamW(m.parameters(), lr=learning_rate)

loss = torch.tensor(0.0)
for steps in tqdm(range(max_iters)):
    xb,yb = get_batch(block_size,batch_size)
    logits,loss = m(xb,yb)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()

print(f"\nFinal loss: {loss.item():.4f}")


print(''.join(decode(m.generate(idx = torch.zeros((1, 1), dtype=torch.long), max_new_tokens=1000)[0].tolist())))


