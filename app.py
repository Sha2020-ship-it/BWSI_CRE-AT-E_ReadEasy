from __future__ import division, print_function
import sys
import os
import pandas as pd
import openai
from flask import Flask, request, render_template
import utils

with open('data\\api.txt', 'r') as f:
    data = f.readlines()
    OPENAI_KEY = data[0]

openai.api_key = OPENAI_KEY
os.environ['OPENAI_API_KEY'] = OPENAI_KEY

# Define a flask app
app = Flask(__name__)

# default config
host = 'localhost'
port = 8000
debug = False

age_ratings = pd.read_excel('data\\AoA_ratings_Kuperman_et_al_BRM.xlsx')
age_ratings = age_ratings[['Word', 'Rating.Mean']]
print(age_ratings)

# CLI arguments of custom config
try:
    host = sys.argv[1]
    port = sys.argv[2]
    debug = sys.argv[3]
except:
    pass


@app.route('/', methods=['GET'])
def index():
    # Main page
    return render_template('index.html', processed_text='Output Here.')

@app.route('/generate', methods=['POST'])
def upload():
    if request.method == 'POST':
        data = dict(request.form)
        processed_text = utils.replace_story(data['story'], int(data['age']))
        return render_template('generate.html', processed_text=processed_text, story=data['story'], title=data['title'], threshold=data['age'])

if __name__ == '__main__':
    app.run(host, port, debug)