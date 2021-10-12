# Super Config
This module is based on the ConfigParser class and provides a basic configuration language (in MS INI format) with structs supporting field types:
* string
* int 
* float
* bool
* collections (nested)
  * array
  * dict
* compiled regex pattern
* cross-references (in-file and cross-file)
  * section reference
  * field reference
* templating (in-file and cross-file)
  * section inheritance


## Example
File `data_delo.cfg`
```ini
[fs::solaris]
root = /Users/tigor/Projects/DeepWriter/pipelines

[fs::hal00]
root = /home/tigor/projects/deep_writer/pipelines

[fsd::delo_articles]
path = delo/articles

[tokenizer::roberta]
factory = tokenizer.RobertaTokenizerFactory
vocab_size = None
min_frequency = 1
initial_alphabet = tokenizers.pre_tokenizers.ByteLevel.alphabet
special_tokens = [ <|eop|>, <|sec|>, <|eos|>, <|eot|> ]
show_progress = false

[tokenizer::roberta-32000(roberta)]
vocab_size = 32000

[tokenizer::roberta-16384(roberta)]
vocab_size = 16384

[ds::delo_roberta]
fsd = fsd::delo_articles
builder = delo_articles_dataset.py
ds_name = all
subdir = delo_roberta
builder_include_only_text_sections = true
builder_section_separation = PARAGRAPH_SEPARATOR
builder_paragraph_separator = '<|eop|>'
seed = 666
;builder_text_preprocessor_rigidity = HIGH

[ds::delo_roberta-part(delo_roberta)]
ds_name = part
subdir = delo_roberta-part

[slider::text-space-0.5]
window_size = None
window_step = 0.5
alignment = SPACE
adaptive = true
leading_edge = None
trailing_edge = None
edge_for_every_sample = None
edge_insets = None
#
slide_func = 'functions.slide_text_batch'
batch_size = 512

[slider::roberta-512(text-space-0.5)]
edge_insets = 1
window_size = 512

[tokenized-ds::tokens-64]
seq_len = 64
truncation = false

[tokenized-ds::tokens-512]
seq_len = 512
truncation = false

[splitter::90-10]
test_part = 0.1
seed = 1111
validation_part = None

[splitter::90-5-5]
test_part = 0.1
validation_part = 0.5
seed = 1111

[function::wordcount]
function = 'functions.dump_wordcount_table'
filename = wordcount.txt

[function::sentencizer-slo]
function = 'sentencizer.sentencize_batch'
sentence_separator = <|eos|>
rigidity = HIGH
cpu_load = 0.4
remove_columns = None
batch_size = 256

[function::normalizer]
function = text_soup.normalize_batch
rigidity = HIGH
cpu_load = 0.4
# remove all columns
remove_columns = [*]
batch_size = 256

[ds::delo_roberta-tokens-preloaded]
fs = fs::hal00
fsd = fsd::delo_articles
dir = 'delo_roberta/normalizer/sentencizer_slo/roberta_512/tokens_512/90-5-5/'
segments = ('test', 'train', 'validation')

[ds::delo_roberta-part-tokens-preloaded]
fs = fs::hal00
fsd = fsd::delo_articles
dir = 'delo_roberta-part/normalizer/sentencizer_slo/roberta_512/tokens_512/90-5-5'
segments = ['test', 'train', 'validation']

[pipeline::delo_roberta-part]
fs = fs::solaris
fsd = fsd::delo_articles
build = [ds::delo_roberta-part, tokenizer::roberta-16384, function::normalizer, function::sentencizer-slo, slider::roberta-512, tokenized-ds::tokens-512, splitter::90-5-5]
cpu_load = 0.85

[pipeline::delo_roberta]
fs = fs::hal00
fsd = fsd::delo_articles
build = [ds::delo_roberta, tokenizer::roberta-16384, function::normalizer, function::sentencizer-slo, slider::roberta-512, tokenized-ds::tokens-512, splitter::90-5-5]
cpu_load = 0.9


```

File `train.cfg`
```ini
[pipeline::train-delo_roberta]
fs=fs::hal00@data-delo
fsd = fsd::delo_articles@data-delo
build = [ds::delo_roberta-tokens-preloaded@data-delo]
cpu_load = 0.9

[pipeline::train-delo_roberta-part]
fs=fs::solaris@data-delo
fsd = fsd::delo_articles@data-delo
build = [ds::delo_roberta-part-tokens-preloaded@data-delo]
cpu_load = 0.9
```

### For more examples see tests/test_cfg.py

## Usage

```python
# file: conf/example.cfg
"""
[a::template]
field_a = 99_999

[a::1(template)]
filed_b = [1, 2, 3]
pattern_1 = pattern:^hello:\s*(\d)+$
ref_b = b::1

[a::2(1)]
filed_b = [3, 2, 1]
ref_b = b::2

[b::1]
say_1 = 'all those moments will be lost in time ...'
say_2 =  c::x/somebody


[b::2(1)]
say_1 = 'other text'
say_2 =  c::x/somebody_else

[c::x]
somebody = "say something else"
somebody_else = "say the same"
"""


def main():
    cfg = Cfg.parse('conf/example.cfg')
    a1 = cfg['a::1']
    print(a1.all_fields)
    a2 = cfg['a::2']
    print(a2.pattern_1.match('hello:  11') is not None)


if __name__ == '__main__':
    main()
