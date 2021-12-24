from main import *
from tensorflow.keras.models import load_model
from PIL import Image
import io

model = load_model('effnet_model/efficientnetB3_0.77.h5')
image_path = 'test_images/1.jpg'

img = Image.open(image_path)

img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
img_bytes = img_bytes.getvalue()

gm = GenImage(image_bytes=img_bytes,
              model=model,
              forms_root='forms_processed',
              fonts_root='Fonts',
              seg_model_path='mobile_net_model',
              text='Лучшая аниме девочка на планете земля мне похуй')

res = gm.generate()

print(res)
