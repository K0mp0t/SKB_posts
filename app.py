from flask import Flask, request, abort, render_template, flash, redirect, Response
from base64 import b64decode, b64encode
from PIL import Image
import io
import json
from proto_v2 import main
import os
from tensorflow.python.keras.models import load_model
import time

app = Flask(__name__, static_folder='static')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

ESTIMATOR = load_model('proto_v2/effnet_model/efficientnetB3_0.77.h5')

FORMS_ROOT = 'proto_v2/forms_processed'
FONTS_ROOT = 'proto_v2/Fonts'
SEG_MODEL_PATH = 'proto_v2/mobile_net_model'


def generate_images(path, img_bytes, estimator, forms_root, fonts_root, seg_model_path, text):
    generator = main.GenImage(path, image_bytes=img_bytes,
                              model=estimator, forms_root=forms_root, fonts_root=fonts_root,
                              seg_model_path=seg_model_path, text=text)

    return generator.generate()


@app.route('/generate', methods=['GET', 'POST', 'OPTIONS'])
def generate():
    if request.method == 'POST':
        if request.json:
            if 'text' not in request.json or 'image' not in request.json:
                abort(400)
            text = request.json.get('text', '')
            if text == '':
                abort(400)
            img_data = b64decode(request.json.get('image', ''))
            img = Image.open(io.BytesIO(img_data))

            img_path = os.path.join(app.root_path, 'proto_v2', 'temp.png')

            img.save(img_path)
            images = generate_images(img_path, io.BytesIO(img_data), ESTIMATOR, FORMS_ROOT, FONTS_ROOT, SEG_MODEL_PATH, text)
            os.remove(img_path)

            encoded_images = list()

            for image in images:
                img_arr = io.BytesIO()
                image.save(img_arr, 'PNG')
                img_arr.seek(0)

                encoded_images.append(b64encode(img_arr.getvalue()).decode('utf-8'))

            return Response(json.dumps({'images': encoded_images}), headers={'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}), 201

        elif request.files:
            file = request.files['file']
            text = request.form['text']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            img = Image.open(file)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()

            img_path = os.path.join(app.root_path, 'proto_v2', 'temp.png')

            img.save(img_path)

            start = time.time()

            images = generate_images(img_path, img_bytes, ESTIMATOR, FORMS_ROOT, FONTS_ROOT, SEG_MODEL_PATH, text)

            end = round(time.time() - start, 2)

            os.remove(img_path)

            encoded_images = list()
            for image in images:
                img_arr = io.BytesIO()
                image.save(img_arr, 'PNG')
                img_arr.seek(0)

                encoded_images.append(b64encode(img_arr.getvalue()).decode('utf-8'))

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
def print_paths():
    return '/generate: accepts POST requests with json dict {"image": base64, "text": string}'


if __name__ == '__main__':
    app.run(host='localhost', port=20210, debug=True)
