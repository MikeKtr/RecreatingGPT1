# Recreating GPT-1

A PyTorch implementation of a character-level GPT (Decoder-only Transformer) trained from scratch on IBM IMS 15.6 documentation in attempt to generate example page of documentation.

## Project Structure

```
.
├── train.py                # Main script: model architecture, training loop, generation
├── scraper/
│   ├── clean_txt.py        # PDF extraction, Unicode normalization & document cleaning
│   └── ims15_6_clean.txt   # Cleaned 36MB dataset (96 printable ASCII characters)
└── README.md
```

## Architecture Details

- **Model Type**: Decoder-only Transformer (GPT architecture)
- **Tokenization**: Character-level (Vocabulary size: 96)
- **Embedding Dimension (`n_embed`)**: 128
- **Context Window (`block_size`)**: 64 tokens
- **Attention Heads (`n_head`)**: 4 heads per layer
- **Transformer Blocks**: 4 blocks
- **Activation Function**: GELU
- **Optimizer**: AdamW (`lr = 1e-3`) with `CosineAnnealingLR` decay scheduler
- **Performance**: Reaches a final cross-entropy loss of **~1.47** after 5,000 iterations.

## Example Generated Output

```text
physical
subsystem are modificator by namement DEDB parameter.
Availability mode threstart the haseader.
IMS RDDSN, user is normal message affound the keystallenteand is particulated in be reorgganized.
TRAGROCONSP call recovery program. If all to only change sules when tile operatoming to Resyntax returns external non- Name
Table numbers continues.
X'94'
(Senubt Edicate excepts, and data sets. Tose elor table Returned defined-deseting.
Enly rulate exit routine with this
command
command codes of the moder

mapping by program to the messagefingth the ETE command trace ability, phasses many all valents, but first sime:
You use a dopects because the keyby issuing uposing internal.
The muster delete
iskey a system betword BB accommumF DMBLID is no included by using the CATIPs in resitue that determined field was installing connectent
(when has bieh
remote 121)
Sever definition and and databases 10
IPC or IMS processing to the internal posith
database virsting include the REUQRE's works and
```
