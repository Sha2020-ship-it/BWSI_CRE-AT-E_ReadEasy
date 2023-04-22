import pandas as pd
import string
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
import openai

ratings = pd.read_excel('data\\AoA_ratings_Kuperman_et_al_BRM.xlsx')
punc = """!@#$%^&*()_+{}:"<>?-=[]\;',./`~"""
API_KEY = open('data\\api.txt').read()
openai.api_key = API_KEY

def pos_tagger(nltk_tag):
    if nltk_tag.startswith('J'):
        return wordnet.ADJ
    elif nltk_tag.startswith('V'):
        return wordnet.VERB
    elif nltk_tag.startswith('N'):
        return wordnet.NOUN
    elif nltk_tag.startswith('R'):
        return wordnet.ADV
    else:         
        return None

def clean(story):
    result = []
    sentences = nltk.sent_tokenize(story)
    for i in sentences:
        b = i.replace("\n", ' ')
        b = b.translate(str.maketrans('', '', string.punctuation))
        b = b.lower()
        b = b.split(' ')
        b = ' '.join([i for i in b if (i != '')])
        result.append(b)
    return result

def lemmatiz(sentence):
    lemmatizer = WordNetLemmatizer()
    pos_tagged = nltk.pos_tag(nltk.word_tokenize(sentence)) 
    wordnet_tagged = list(map(lambda x: (x[0], pos_tagger(x[1])), pos_tagged))

    lemmatized_sentence = []
    for word, tag in wordnet_tagged:
        if tag is None:
            lemmatized_sentence.append(word)
        else:       
            lemmatized_sentence.append(lemmatizer.lemmatize(word, tag))
    lemmatized_sentence = " ".join(lemmatized_sentence)

    return lemmatized_sentence

def get_word_meaning(word, sentence):
    word_meaning = None
    words = nltk.word_tokenize(sentence)
    pos_tags = pos_tag(words)

    pos_map = {'N': 'n', 'V': 'v', 'R': 'r', 'J': 'a'}
    word_pos_tag = None
    for word_tag in pos_tags:
        if word in word_tag:
            nltk_pos_tag = word_tag[1][0].upper()
            word_pos_tag = pos_map.get(nltk_pos_tag)
            break

    if word_pos_tag:
        synsets = wordnet.synsets(word, pos=word_pos_tag)
        if synsets:
            word_meaning = synsets[0].definition()

    return word_meaning

def find_complicated(story, threshold = 0):
    complicated = {}
    story_clean = clean(story)
  
    over = set()
    for i in story_clean:
        for j in i.split():
            k = lemmatiz(j)
            if k in list(ratings['Word']):
                if list(ratings[ratings['Word'] == k]['Rating.Mean'])[0] > threshold:
                    over.add(j)

    over = list(over)
    for i in over:
        if i not in complicated.keys():
            complicated[i] = []
    
    sentences = nltk.sent_tokenize(story)
    for i in over:
        for j in sentences: 
            for k in j.split():
                if i == k:
                    complicated[i].append(j)
    print(complicated)
    return complicated

def find_best_replacement(word, sentence, words_to_compare):
    tokens = nltk.word_tokenize(sentence)
    word_synsets = wordnet.synsets(word)
    similarities = {}
    for compare_word in words_to_compare:
        compare_word_synsets = wordnet.synsets(compare_word)
        for word_synset in word_synsets:
            for compare_word_synset in compare_word_synsets:
                similarity = word_synset.path_similarity(compare_word_synset)
                if similarity is not None:
                    similarities[compare_word] = max(similarity, similarities.get(compare_word, 0))
    print(similarities)
    if len(similarities.keys()) == 0:
        best_word = word
    else:
        best_word = max(similarities, key=similarities.get)
    return best_word


def find_alternate_words(complicated, threshold):
    replacements = {}
    definitions = {}

    for i in complicated.keys():
        replacements[i] = []
        definitions[i] = []

    for i in definitions.keys():
        for j in complicated[i]:
            definitions[i].append(get_word_meaning(i, j))
    print(definitions)
    
    for i in definitions.keys():
        for j in range(len(definitions[i])):
            prompt = f"""Give me a numbered list of 10 SIMPLE words that corresponds to this definition: '{definitions[i][j]}'. Make sure the list does not include the word: {i}."""
            gc = openai.Completion.create(model="text-davinci-003",prompt=prompt,temperature=0.7,max_tokens=256,top_p=1,frequency_penalty=0,presence_penalty=0)
            response = gc.choices[0].text

            list_without_numbers = [line.split(". ")[1] for line in response.split("\n") if line.strip()]
            off = []

            for m in list_without_numbers:
                n = lemmatiz(m.lower().strip())
                if n in list(ratings['Word']):
                    if list(ratings[ratings['Word'] == n]['Rating.Mean'])[0] <= threshold:
                        off.append(n)
            print(off)
            replacements[i].append(find_best_replacement(i, complicated[i][j], off))

    return replacements

def replace_story(story, threshold):
    complicated = find_complicated(story, threshold)
    replacements = find_alternate_words(complicated, threshold)
    tokens = nltk.word_tokenize(story)
    for i in range(len(tokens)):
        if tokens[i] in replacements.keys():
            tokens[i] = f'[{replacements[tokens[i]][0]}]'
    changed = ' '.join(tokens)
    prompt = f"""{changed}\n\nONLY FIX THE TENSE OF THE WORDS IN BRACKETS. DO NOT CHANGE ANY OTHER WORDS! THIS IS CRUCIAL!"""
    gc = openai.Completion.create(model="text-davinci-003",prompt=prompt,temperature=0.7,max_tokens=1101,top_p=1,frequency_penalty=0,presence_penalty=0)
    response = gc.choices[0].text
    return (response)
