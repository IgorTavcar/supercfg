# Super Config
This module is based on the ConfigParser class and provides a basic configuration language (in MS INI format) with structs of fields with types:
* int
* float
* string
* exp int (3e10)
* exp float (3e-7)
* bool
* list
* compiled regex pattern
* section reference
* field reference
* cross-file section/field reference


## Example
File `test_minigpt_trainer_builder.cfg`
```ini
[model::minigpt_articles-small]
embd_pdrop = 0.1
resid_pdrop = 0.1
attn_pdrop = 0.1
n_layer = 8
n_head = 8
n_embd = 512
; vocab_size
; ... derived from tokenizer
vocab_size = dataset::articles-mini-part-64/layout/tokenizer/vocab_size@articles_mini_part
; block_size aka max_seq_len
; ... derived from layout
block_size = dataset::articles-mini-part-64/layout/window_size@articles_mini_part

[trainer::minigpt_articles-mini-part-64]
fs = fs::articles@articles
dataset = dataset::articles-mini-part-64@articles_mini_part
model = model::minigpt_articles-small
;
max_epochs = 10
batch_size = 64
learning_rate = 3e-4
betas = (0.9, 0.95)
grad_norm_clip = 1.0
; # only applied on matmul weights
weight_decay = 0.1
; learning rate decay params:
; ... linear warmup followed by cosine decay to 10% of original
lr_decay = false
; these two numbers come from the GPT-3 paper,
; ... but may not be good defaults elsewhere
warmup_tokens = 375e6
; ... at what point we reach 10% of original LR
final_tokens = 260e9

```

File `articles_mini_part.cfg`
```ini
[fs::articles]
root = ../data
domain = 'articles'

[importer::articles_mini_part-no_sections]
source = ../data/corpus/slovenian/part1/raw_text_only_digital_text_chunks_mini_part
source_pattern = pattern:^chunk\.[a-z]{3}$
destination_fs = fs::articles
destination_ds = articles_part-no_sections
process = process.IDXArticleImporterProcess
article_sections = false

[tokenizer::gpt-bpe-5_000]
fs = fs::articles
target_model = gpt
vocab_size = 5_000
add_prefix_space = true

[layout::64-0.5]
tokenizer = tokenizer::gpt-bpe-5_000
process = 'process.Aligner'
window_size = 64
window_step = 0.5
alignment = space
adaptive = true
edge_tokens = (<|eot|>, <|eot|>, false)

[dataset::articles-mini-part-64]
fs = fs::articles
importer = importer::articles_mini_part-no_sections
layout = layout::64-0.5
tag = "0.5"
target_tasks = (causal_language_modeling, masked_language_modeling)
parts = (train=0.9, test=0.1)
```

For more code see tests/test_supercfg.py

## Usage

```python
from supercfg import Cfg

# file: cfg/example.cfg
"""
[a::1]
filed_a = 100_000
filed_b = (1, 2, 3)
pattern_1 = pattern:^hello:\s*\d$
ref_b = b::1

[a::2]
filed_a = 30_000
filed_b = (1, 2, 5)
pattern_1 = pattern:^hello:\s*(\d{2})$
ref_b = b::1

[b::1]
say_1 = 'all those moments will be lost in time ...'
say_2 =  c::x/somebody

[c::x]
somebody = "say something else"
"""


def main():
    cfg = Cfg.parse('cfg/example.cfg')
    a = cfg['a::1']
    print(a.ref_b.say_2)
    print(a.pattern_1.match('hello: 1') is not None)
    a = cfg['a::2']
    print(a.filed_b[:-1])
    print(a['ref_b/say_1'])
    print(a.pattern_1.match('hello:  11') is not None)


if __name__ == '__main__':
    main()

