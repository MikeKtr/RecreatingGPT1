

import torch
import torch.nn as nn
from torch.nn import functional as F
from tqdm import tqdm

# Hyperparemeters

block_size = 64 # Size of every sample taken for learning
batch_size = 64 # Number of samples taken for learning
max_iters = 5000 # Iterations while learning
learning_rate = 1e-3 # Default learning rate (obsolite bc. of scheduler)
n_embed = 128 # Number of attributes one token has
dropout = 0.2 # Training dropout 
device = 'cuda' if torch.cuda.is_available() else 'cpu'


# This module is designed to create relations between certain tokens in certain location
class Head(nn.Module):
    def __init__(self,head_size):
        super().__init__()
        
        # here you inicialise basically random number for key, queries and value
        # querry represents what relations does the particular token look for 
        self.query = nn.Linear(n_embed, head_size, bias = False)
        # key is representing what does the particular token in particular location represents (answer to querry)
        self.key = nn.Linear(n_embed, head_size, bias=False)
        # value contains values passed to token which querry matches the best 
        self.value = nn.Linear(n_embed, head_size, bias = False)
        # My understinng of the whole query,key,value is that the query is like a search in google, key is keyphrases that
        # help browser provide an ansewr and values are the actual reasults i get

        # Using buffer for optimalisation
        self.register_buffer('tril', torch.tril(torch.ones(block_size, block_size)))
        
        # Dropout randomly deletes some values from tokens to prevend overfitting
        self.dropout = nn.Dropout(dropout)

    def forward(self,x):
        B,T,C = x.shape
        # assigning values of keys and querries to every token in x
        k = self.key(x)
        q = self.query(x)

        # Multiplying q * k works like matching the best keys to every querries. you have to transpose k
        wei = q @ k.transpose(-2,-1) * k.shape[-1]**-0.5
        # using masking and softmax to make weights a triangular matrix
        wei = wei.masked_fill(self.tril[:T, :T] == 0, float('-inf'))
        wei = F.softmax(wei, dim=-1)
        
        # using dropout to prevent overfitting
        wei = self.dropout(wei)

        # taking the values for every token
        v = self.value(x)
        # adjusting current values with weights
        out = wei @ v

        return out

# This allows to use multiple heads at once instead of one big head
# This is usefull because every head generates its own weights for key,queries and values and all of them specialises
# in different things
class MultiHeadAttention(nn.Module):

    def __init__(self,num_heads,head_size):
        super().__init__()
        self.heads = nn.ModuleList([Head(head_size) for _ in range(num_heads)])
        self.proj = nn.Linear(n_embed, n_embed)
        self.dropout = nn.Dropout(dropout)

    def forward(self,x):
        out = torch.cat([h(x) for h in self.heads], dim = -1)
        out = self.dropout(self.proj(out))
        return out  

# This module allows the model to process the information it recieved from "Head" step
# It consist of several steps:
# 1. quadrupuling the amount of token's atrubutes 
# 2. uses GELU/ReLU to make negative weitghts more neglagable or delates them compleately
# 3. Transforms the result to be it's original size
# 4. Dropout to prevent overfitting
class FeedFoward(nn.Module):

    def __init__(self,n_embed):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_embed,4 * n_embed),
            nn.GELU(),
            nn.Linear(4 * n_embed, n_embed),
            nn.Dropout(dropout),
        )
    def forward(self,x ):
            return self.net(x)

#Block organises the learinig steps
class Block(nn.Module):

    def __init__(self, n_embed, n_head):
        super().__init__()
        head_size =n_embed // n_head
        self.sa = MultiHeadAttention(n_head,head_size)
        self.ffwd = FeedFoward(n_embed)
        #Scales the values so for every token the average is 0 and divergence is 1
        self.ln1 = nn.LayerNorm(n_embed)
        self.ln2 = nn.LayerNorm(n_embed)


    def forward(self,x):
        x = x + self.sa(self.ln1(x))
        x = x + self.ffwd(self.ln2(x))
        return x

# The brain of the whole model.
# Here there are combined all of the building blocks

class BigramLanguageModel(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()

        # Number of tokens used (here it's the number of unique letters in text)
        self.vocab_size = vocab_size
        # This builds 2D matrix, vocab_size x n_embed and will hold all the relations between tokens
        self.token_embedding_table = nn.Embedding(vocab_size, n_embed)
        # This builds 2D matrix, block_size x n_embed and will hold all the relations between positions of tokens in given batch
        self.position_embedding_table = nn.Embedding(block_size, n_embed)

        # This chains the building blocks and executes them in order
        self.blocks = nn.Sequential(
            Block(n_embed, n_head=4),
            Block(n_embed, n_head=4),
            Block(n_embed, n_head=4),
            Block(n_embed, n_head=4),
            nn.LayerNorm(n_embed),
        )

        self.lm_head = nn.Linear(n_embed, vocab_size)

    def forward(self,idx,targets=None):


        B,T = idx.shape
        # idx is size B x T, this line takes the values of each token and glues to them the corresponeding vector from the embeding table
        tok_emb = self.token_embedding_table(idx) #(B,T,C)
        # similar to line above but it uses posiiton embeding table
        pos_emb = self.position_embedding_table(torch.arange(T,device=device)) #(T,C)
        # adds both of obove togeter
        x = tok_emb + pos_emb #(B,T,C)

        # goes thrue blocks defined in __init__
        x = self.blocks(x)

        # takes into accout the positions of tokens
        logits = self.lm_head(x) #(B,T,vocab_size)

        

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
            idx_cond = idx[:,-block_size:]
            logits, _ = self(idx_cond)

            logits = logits[:,-1,:]
            probs = F.softmax(logits,dim=-1)
            idx_next = torch.multinomial(probs,num_samples=1)
            idx = torch.cat((idx,idx_next),dim=1)
        return idx


# Reading text from file
def get_text():
    with open('./scraper/ims15_6_clean.txt','r',encoding='utf-8') as f:
        text = f.read()
        print("length of ds: ", len(text))
        chars = sorted(list(set(text)))
        print("characters: ",chars)
        print("length of chars: ", len(chars))
        return text,chars


# Generating the batch
def get_batch(block_size,batch_size,type='train'):
    data = train_data if type == 'train' else val_data
    ix = torch.randint(len(data) - block_size, (batch_size,))
    x = torch.stack([data[i:i+block_size] for i in ix])
    y = torch.stack([data[i+1:i+block_size+1] for i in ix])
    x,y = x.to(device),y.to(device)
    return x,y


text, chars = get_text()
vocab_size = len(chars)
# Translation from numbers to letters and the other way  
stoi = {ch:i for i,ch in enumerate(chars)}
itos = {i:ch for i,ch in enumerate(chars)}
encode = lambda s: [stoi[c] for c in s]
decode = lambda c: [itos[i] for i in c]



data = torch.tensor(encode(text), dtype=torch.long)

n = int(0.9*len(data))

# preparing training data and validation data
train_data = data[:n]
val_data = data[n:]

# init the biagramModel
m = BigramLanguageModel(vocab_size)
m.to(device)

# setting optimizer
optimizer = torch.optim.AdamW(m.parameters(), lr=learning_rate)
# setting scheduler to adjust the learing rate as the training progresses
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_iters, eta_min=1e-6)


# Main loop, the hearth of all the learning
loss = torch.tensor(0.0)
for steps in tqdm(range(max_iters)):
    # preparing batch
    xb,yb = get_batch(block_size,batch_size)
    # calculates logits and how wrong they ware
    logits,loss = m(xb,yb)
    # clears old gradients
    optimizer.zero_grad(set_to_none=True)
    # Backward pass, propagation
    loss.backward()
    # updating the weights 
    optimizer.step()
    # resizing the learning rate 
    scheduler.step()


print(f"\nFinal loss: {loss.item():.4f}")


print(''.join(decode(m.generate(idx = torch.zeros((1, 1), dtype=torch.long, device=device), max_new_tokens=1000)[0].tolist())))


