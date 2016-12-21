"""Get words from files in "src/dictionary/"."""

import os

def getWordList(filepath):
    """
    Get a list of words from a file.
    
    Input: file name
    Output: dict with formula {word: [synonym, synonym]}"""
    assert os.path.isfile(filepath), 'Must be a file'
    txt = open(filepath).read().strip().split('\n')
    if ':' in open(filepath).read():
        for line in txt:
            if ':' not in line:
                txt[txt.index(line)] = line + ':'
        words = {}
        for line in txt:
            index = line.split(':')[0]
            words[index] = line.split(':')[1].split(',')
            for syn in words[index]:
                if syn == '':
                    words[index].remove(syn)
    else:
        words = [word.strip() for word in txt]
    return words


verbs = getWordList('src/dictionary/verbs.txt')
nouns = getWordList('src/dictionary/nouns.txt')
extras = getWordList('src/dictionary/extras.txt')
directions = getWordList('src/dictionary/directions.txt')
