from flask import Blueprint, render_template, request, current_app
import json, os
import bardapi, openai
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import util.chatbot_util as cu
from urllib.parse import unquote

chatbot_bp = Blueprint('chatbot_bp', __name__)

menu = {'ho':0, 'us':0, 'cr':0, 'ma':0, 'cb':1, 'sc':0}

@chatbot_bp.before_app_first_request
def before_app_first_request():
    global model, wdf
    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    filename = os.path.join(current_app.static_folder, 'data/wellness_dataset.csv')
    wdf = pd.read_csv(filename)
    wdf.embedding = wdf.embedding.apply(json.loads)
    print('Wellness initialization is done.')

@chatbot_bp.route('/counsel', methods=['GET','POST'])
def counsel():
    if request.method == 'GET':
        return render_template('chatbot/counsel.html', menu=menu)
    else:
        user_input = request.form['userInput']
        embedding = model.encode(user_input)
        wdf['유사도'] = wdf.embedding.map(lambda x: cosine_similarity([embedding],[x]).squeeze())
        answer = wdf.loc[wdf.유사도.idxmax()]
        result = {
            'category':answer.구분, 'user':user_input, 'chatbot':answer.챗봇, 'similarity':answer.유사도
        }
        return json.dumps(result)

@chatbot_bp.route('/counsel_rest')
def counsel_rest():
    user_input = unquote(request.args.get('userInput'))
    embedding = model.encode(user_input)
    wdf['유사도'] = wdf.embedding.map(lambda x: cosine_similarity([embedding],[x]).squeeze())
    answer = wdf.loc[wdf.유사도.idxmax()]
    result = {
        'category':answer.구분, 'user':user_input, 'chatbot':answer.챗봇, 'similarity':answer.유사도
    }
    return json.dumps(result)

@chatbot_bp.route('/legal', methods=['GET','POST'])
def legal():
    if request.method == 'GET':
        return render_template('chatbot/legal.html', menu=menu)
    else:
        user_input = request.form['userInput']
        res_dict = cu.get_legal_answer(current_app.static_folder, user_input)
        res_dict['user'] = user_input
        return json.dumps(res_dict)

@chatbot_bp.route('/bard', methods=['GET','POST'])
def bard():
    if request.method == 'GET':
        return render_template('chatbot/bard.html', menu=menu)
    else:
        with open(os.path.join(current_app.static_folder, 'keys/bardApiKey.txt')) as file:
            os.environ['_BARD_API_KEY'] = file.read()
        user_input = request.form['userInput']
        response = bardapi.core.Bard().get_answer(user_input)
        result = {'user':user_input, 'chatbot':response['content']}
        return json.dumps(result)

@chatbot_bp.route('/genImg', methods=['GET','POST'])
def gen_img():
    if request.method == 'GET':
        return render_template('chatbot/genImg.html', menu=menu)
    else:
        with open(os.path.join(current_app.static_folder, 'keys/openAiApiKey.txt')) as file:
            openai.api_key = file.read()
        user_input = request.form['userInput'] 
        size = request.form['size']

        gpt_prompt = [
            {'role': 'system', 
             'content': 'Imagine the detail appearance of the input. Response it shortly around 20 English words.'},
            {'role': 'user', 'content': user_input}      
        ]
        gpt_response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo', messages=gpt_prompt
        )
        prompt = gpt_response['choices'][0]['message']['content']
        dalle_response = openai.Image.create(
            prompt=prompt, size=size         # '1024x1024', '512x512', '256x256'
        )
        img_url = dalle_response['data'][0]['url']
        result = {'img_url':img_url, 'translated_text': prompt}
        return json.dumps(result)
    
@chatbot_bp.route('/ocr', methods=['GET','POST'])
def ocr():
    if request.method == 'GET':
        return render_template('chatbot/ocr.html', menu=menu)
    else:
        color = request.form['color']
        showText = request.form['showText']
        size = request.form['size']
        file_image = request.files['image']
        filename = os.path.join(current_app.static_folder, f'upload/{file_image.filename}')
        file_image.save(filename)

        text, mtime = cu.proc_ocr(current_app.static_folder, filename, color, showText, size)
        result = {'text':text, 'mtime':mtime}
        return json.dumps(result)

@chatbot_bp.route('/yolo', methods=['GET','POST'])
def yolo():
    if request.method == 'GET':
        return render_template('chatbot/yolo.html', menu=menu)
    else:
        color = request.form['color']
        linewidth = int(request.form['linewidth'])
        fontsize = int(request.form['fontsize'])
        file_image = request.files['image']
        img_file = os.path.join(current_app.static_folder, f'upload/{file_image.filename}')
        file_image.save(img_file)

        mtime = cu.proc_yolo(current_app.static_folder, img_file, color, linewidth, fontsize)
        return json.dumps(str(mtime))
