import string
import random
import csv
import sys
import numpy
import pickle
import wget
import zipfile
import os
import math
from nltk.corpus import wordnet
from collections import defaultdict

### Util ###

def get_char_type(char):
    if char in string.ascii_letters:
        return 0
    elif char in string.digits:
        return 1
    else:
        return 2

def get_token_name(token):
    return str(get_char_type(token[0])) + str(len(token))

def read_sweetword_set(filename):
    with open(filename) as f:
        return [row for row in csv.reader(f)]

### PCFG Parse ###

def parse_string_cfg(s):
    token, state, grammar = " ", 0, []
    transition = [
        #Letter, Digit, Puncutation
        [1, 2, 3], # Out
        [4, 2, 3], # First Letter
        [1, 5, 3], # First Digit
        [1, 2, 6], # First Punctuation
        [4, 2, 3], # In Letter
        [1, 5, 3], # In Digit
        [1, 2, 6]  # In Puncuation
    ]
    for char in s:
        char_type = get_char_type(char)
        state = transition[state][char_type]
        if state in [1, 2, 3]:
            grammar.append((get_token_name(token), token))
            token = char
        else:
            token += char
    grammar.append((get_token_name(token), token))
    return grammar[1:]

def download_pickles_zip():
    print "Downloading Pickle!"
    download_success = False
    file_url = "https://s3.amazonaws.com/afkfurion/pickles.zip"
    while not download_success:
        try:
            file_name = wget.download(file_url)
            download_success = True
            print
        except Exception, e:
            print e
            print "Download Failed. Please check your network connection."

def unzip_pickles():
    print "Unzipping PCFG Pickles!"
    with zipfile.ZipFile("pickles.zip", 'r') as f:
        f.extractall()

def load_pickles():
    print "Loading Pickles!"
    with open("grammar.pickle", "r") as grammar_file:
        start = pickle.load(grammar_file)
    with open("terminal.pickle", "r") as terminal_file:
        term = pickle.load(terminal_file)
    return start, term

def clean_up():
    print "Cleaning Up!"
    os.remove("grammar.pickle")
    os.remove("terminal.pickle")
    os.remove("pickles.zip")

### Get probability score for honeyword ###

def get_default_min_prob(prob_distrib):
    probs = [i for i in prob_distrib.values() if i > 0]
    if len(probs) > 0:
        return min(probs)
    return 1.0

def get_default_empty_prob(prob_distrib):
    return get_default_min_prob(prob_distrib) / 10.0

def get_default_digit_prob(seq, prob_distrib):
    if all(int(seq[i]) - int(seq[i-1]) for i in range(1, len(seq))) or (
        int(seq) > 1900 and int(seq) < 2016):
        return get_default_min_prob(prob_distrib)
    else:
        return get_default_empty_prob(prob_distrib)

def get_default_letter_prob(seq, prob_distrib):
    if wordnet.synsets(seq):
        return get_default_min_prob(prob_distrib)
    else:
        return get_default_empty_prob(prob_distrib)

def get_default_seq_prob(token, seq, terminal):
    if token[0] == "0":
        return get_default_letter_prob(seq, terminal[token])
    elif token[0] == "1":
        return get_default_digit_prob(seq, terminal[token])
    else:
        return get_default_empty_prob(terminal[token])

def get_sweetword_score(string, start, term):
    tokens = parse_string_cfg(string)
    grammar, log_seq_prob = [], []
    for token, seq in tokens:
        grammar.append(token)
        if token in term and seq in term[token] and term[token][seq] > 0:
            log_seq_prob.append(math.log(term[token][seq]))
        else:
            log_seq_prob.append(math.log(get_default_seq_prob(token, seq, term)))
    if tuple(grammar) in term and start[tuple(grammar)] > 0:
        log_grammar_prob = math.log(start[tuple(grammar)])
    else:
        log_grammar_prob = math.log(get_default_empty_prob(start))
    return sum([log_grammar_prob] + log_seq_prob)

def get_max_prob_index(sweetwords, start, term):
    max_score, max_idx = -sys.maxint, 0
    for i in range(len(sweetwords)):
        score = get_sweetword_score(sweetwords[i], start, term)
        if score > max_score:
            max_score, max_idx = score, i
    return max_idx + 1

def get_sweetword_index_set(sweetword_set, start, term):
    return [str(get_max_prob_index(s, start, term)) for s in sweetword_set]

if len(sys.argv) != 4:
    print "Generate the honeywords."
    print ""
    print "python pcfg.py n m filename"
    print ""
    print "     m               sweetword sets"
    print "     n               sweetwords (fields)"
    print "     filename        the filename of input"
    sys.exit(1)

download_pickles_zip()
unzip_pickles()
start, term = load_pickles()
sweetword_set = read_sweetword_set(sys.argv[3])
print ",".join(get_sweetword_index_set(sweetword_set, start, term))
clean_up()