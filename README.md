# Recreating GPT-1

A PyTorch implementation of a character-level GPT (Decoder-only Transformer) trained from scratch on IBM IMS 15.6 documentation.

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

## Setup & Running

### Requirements
```bash
pip install torch tqdm pymupdf
```

### Running Training & Text Generation
To train the model and generate sample text:
```bash
python train.py
```

### Re-cleaning the Corpus
If you wish to re-process or convert the documentation PDFs:
```bash
python scraper/clean_txt.py
```
