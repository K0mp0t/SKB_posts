import requests
import json
from base64 import b64encode
from PIL import Image
import time
import io

# "http://167.71.42.229:20210/generate"
# "http://localhost:5000/generate"

data = Image.open('proto_v2/test_images/1.jpg')
buffer = io.BytesIO()
data.save(buffer, data.format)
img_str = b64encode(buffer.getvalue()).decode('utf-8')

start = time.time()

request = requests.post("http://localhost:5000/generate",
                        data=json.dumps({'image': img_str, 'text': 'Илья клоун'}),
                        headers={'content-type': 'application/json'})

# request = requests.options("http://167.71.42.229:20210/generate")

# response = json.loads(request.content)
print(request.status_code, time.time()-start)