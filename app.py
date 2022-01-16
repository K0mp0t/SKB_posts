import string
from flask import Flask, request, render_template, Response, send_file
from base64 import b64decode, b64encode
from PIL import Image
import io
import json
from proto_v2 import main, segmentation
from tensorflow.python.keras.models import load_model
import time
import psutil
import os
import random


app = Flask(__name__, static_folder='static')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

ESTIMATOR = load_model('proto_v2/effnet_model/efficientnetB3_0.77.h5')
SEG_MODEL = segmentation.DeepLabModel("proto_v2/xception_model")

FORMS_ROOT = 'proto_v2/forms_processed'
FONTS_ROOT = 'proto_v2/Fonts'
# SEG_MODEL_PATH = 'proto_v2/mobile_net_model'

process = psutil.Process(os.getpid())

GENERATORS = dict()
TOKENS_LIFETIME = dict()
TOKENS_INDICES = dict()


def generate_images(img_bytes, estimator, forms_root, fonts_root, seg_model, text):
    generator = main.GenImage(image_bytes=img_bytes, model=estimator, forms_root=forms_root, fonts_root=fonts_root,
                              seg_model=seg_model, text=text)

    return generator.generate()


def generate_token(length):
    return ''.join(random.choice(string.ascii_letters+string.digits) for _ in range(length))


def remove_token_resources(token):
    del GENERATORS[token]
    del TOKENS_LIFETIME[token]
    del TOKENS_INDICES[token]

    for fn in os.listdir(app.static_folder):
        if token in fn:
            os.remove(os.path.join(app.static_folder, fn))

    del token


def prune_tokens():
    for fn in os.listdir(app.static_folder):
        if fn.split('_')[0] not in GENERATORS:
            os.remove(os.path.join(app.static_folder, fn))
    for token, lifetime in TOKENS_LIFETIME.items():
        if time.time() - lifetime > 300:
            remove_token_resources(token)
    while len(TOKENS_LIFETIME) > 15:
        token = max(TOKENS_LIFETIME, key=TOKENS_LIFETIME.get)
        remove_token_resources(token)


@app.route('/api/remove-token', methods=['GET', 'OPTIONS'])
def remove_token():
    if request.method == 'GET':
        token = request.args.get('token', default='*', type=str)

        if token not in GENERATORS or token == '*':
            return Response('invalid token', status=400)

        remove_token_resources(token)

        return Response(status=200)
    elif request.method == 'OPTIONS':
        return Response(status=204, headers={'Access-Control-Allow-Origin': '*',
                                             'Content-Type': 'application/json',
                                             'Access-Control-Allow-Methods': ['POST', 'GET', 'OPTIONS'],
                                             'Access-Control-Allow-Headers': ['X-PINGOTHER', 'Content-Type'],
                                             'Access-Control-Max-Age': 86400})


@app.route('/api/prolong-token', methods=['GET', 'OPTIONS'])
def prolong():
    if request.method == 'GET':
        token = request.args.get('token', default='*', type=str)
        TOKENS_LIFETIME[token] = time.time()

        return Response(status=200)
    elif request.method == 'OPTIONS':
        return Response(status=204, headers={'Access-Control-Allow-Origin': '*',
                                             'Content-Type': 'application/json',
                                             'Access-Control-Allow-Methods': ['POST', 'GET', 'OPTIONS'],
                                             'Access-Control-Allow-Headers': ['X-PINGOTHER', 'Content-Type'],
                                             'Access-Control-Max-Age': 86400})


@app.route('/api/init', methods=['POST', 'OPTIONS'])
def init_generator():
    prune_tokens()

    if request.method == 'POST' and request.json:
        if 'text' not in request.json or 'image' not in request.json:
            return Response(status=400)
        text = request.json.get('text', '')
        if text == '':
            return Response('recieved an empty string', status=400)
        img_data = b64decode(request.json.get('image', ''))

        if img_data == '*' or text == '*':
            return Response('no image or text data', status=400)

        generator = main.GenImage(image_bytes=io.BytesIO(img_data).getvalue(), model=ESTIMATOR, forms_root=FORMS_ROOT,
                                  fonts_root=FONTS_ROOT, seg_model=SEG_MODEL, text=text)

        token = generate_token(10)

        GENERATORS[token] = generator.generate_image_by_image()
        TOKENS_LIFETIME[token] = time.time()
        TOKENS_INDICES[token] = 0

        return Response(json.dumps({'token': token}), status=201)

    elif request.method == 'OPTIONS':
        return Response(status=204, headers={'Access-Control-Allow-Origin': '*',
                                             'Content-Type': 'application/json',
                                             'Access-Control-Allow-Methods': ['POST', 'GET', 'OPTIONS'],
                                             'Access-Control-Allow-Headers': ['X-PINGOTHER', 'Content-Type'],
                                             'Access-Control-Max-Age': 86400})

    return Response('no json recieved', status=400)


@app.route('/api/getnextimage', methods=['GET', 'OPTIONS'])
def get_next_image():
    if request.method == 'GET' or request.method == 'POST':
        token = request.args.get('token', default='*', type=str)
        if token not in GENERATORS or token == '*':
            return Response('invalid token', status=400)

        generated_image = next(GENERATORS[token])
        path = os.path.join('static', f'{token}_{TOKENS_INDICES[token]}.png')
        generated_image.save(path)

        TOKENS_INDICES[token] += 1

        return Response(json.dumps({'url': path}), 200)
    elif request.method == 'OPTIONS':
        return Response(status=204, headers={'Access-Control-Allow-Origin': '*',
                                             'Content-Type': 'application/json',
                                             'Access-Control-Allow-Methods': ['POST', 'GET', 'OPTIONS'],
                                             'Access-Control-Allow-Headers': ['X-PINGOTHER', 'Content-Type'],
                                             'Access-Control-Max-Age': 86400})


# DEPRECIATED
@app.route('/image')
def display_single_image():
    token = request.args.get('token', default='*', type=str)
    index = request.args.get('index', default=-1, type=int)

    if token not in GENERATORS or token == '*':
        return Response('invalid token', status=400)
    if TOKENS_INDICES[token] < index or index < 0:
        return Response('invalid index', status=400)

    if os.path.exists(os.path.join(app.static_folder, f'{token}_{index}.png')):

        return send_file(os.path.join(app.static_folder, f'{token}_{index}.png'), mimetype='image/gif')
    else:
        return Response('image not found, but token and index seem to be ok', status=523)


@app.route('/generate', methods=['GET', 'POST', 'OPTIONS'])
def generate():
    print(f'Mem usage on call: {process.memory_info().rss / 1024 // 1024} MB')
    if request.method == 'POST':
        if request.json:
            if 'text' not in request.json or 'image' not in request.json:
                return Response(status=400)
            text = request.json.get('text', '')
            if text == '':
                return Response(status=400)
            img_data = b64decode(request.json.get('image', ''))

            images = generate_images(io.BytesIO(img_data).getvalue(), ESTIMATOR, FORMS_ROOT, FONTS_ROOT,
                                     SEG_MODEL, text)

            encoded_images = list()

            for image in images:
                img_arr = io.BytesIO()
                image.save(img_arr, 'PNG')
                img_arr.seek(0)

                encoded_images.append(b64encode(img_arr.getvalue()).decode('utf-8'))

            return Response(json.dumps({'images': encoded_images}), headers={'Access-Control-Allow-Origin': '*',
                                                                             'Content-Type': 'application/json'}), 201

        elif request.files:
            file = request.files['file']
            text = request.form['text']
            if file.filename == '':
                return Response(status=400)
            img = Image.open(file)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')

            start = time.time()

            images = generate_images(img_bytes.getvalue(), ESTIMATOR, FORMS_ROOT, FONTS_ROOT, SEG_MODEL, text)

            end = round(time.time() - start, 2)

            encoded_images = list()
            for image in images:
                img_arr = io.BytesIO()
                image.save(img_arr, 'PNG')
                img_arr.seek(0)

                encoded_images.append(b64encode(img_arr.getvalue()).decode('utf-8'))

            print(f'Mem usage before return: {process.memory_info().rss / 1024 // 1024} MB')

            return render_template('gen_output_page.html', encoded_images=encoded_images, end=end)
    elif request.method == 'OPTIONS':
        return Response(status=204, headers={'Access-Control-Allow-Origin': '*',
                                             'Content-Type': 'application/json',
                                             'Access-Control-Allow-Methods': ['POST', 'GET', 'OPTIONS'],
                                             'Access-Control-Allow-Headers': ['X-PINGOTHER', 'Content-Type'],
                                             'Access-Control-Max-Age': 86400})
    else:
        return render_template('gen_input_page.html')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='localhost', port=20210, debug=True, use_reloader=False)
