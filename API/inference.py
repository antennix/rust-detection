from PIL import Image
import numpy as np
import io
import base64
from io import BytesIO
import urllib.request
import boto3
import math
ssm = boto3.client('ssm', region_name='us-east-1')
client = boto3.client('sagemaker-runtime', region_name='us-east-1')
RESIZE = 500

def pil_to_base64(img, format="jpeg"):
    buffer = BytesIO()
    img.save(buffer, format)
    img_str = base64.b64encode(buffer.getvalue()).decode("ascii")
    return img_str

def init(json_body):

    target_array = []

    bytes_decoded = base64.b64decode(json_body['img'])
    im = Image.open(BytesIO(bytes_decoded))
    w, h = im.size

    if im.height < im.width:
        width = RESIZE
        height = round(im.height * width / im.width)
    else:
        height = RESIZE
        width = round(im.width * height / im.height)

    im = im.resize((width, height))

    w, h = im.size
    for row in range(h):
        for column in range(w):
            column = im.getpixel((column, row))
            target_array.append('{},{},{}'.format(column[0], column[1], column[2]))

    current = ssm.get_parameter(Name='XGB_ENDPOINT', WithDecryption=False)
    currentEndpoint = current['Parameter']['Value']

    index = 0
    result_array = []
    while len(target_array[index * 70000:index * 70000 + 70000]) > 0:
        response = client.invoke_endpoint(
            EndpointName=currentEndpoint,
            Body='\n'.join(target_array[index * 70000:index * 70000 + 70000]),
            ContentType='text/csv',
            Accept='application/json'
        )
        result = response['Body'].read().decode()
        result_array = result_array + result.split(',')
        index = index + 1

    newImg = Image.new("RGB", (w, h))
    newImg.paste(im)
    counter = 0
    index = 0
    for row in range(h):
        for column in range(w):
            if(result_array[index] == '1.0'):
                newImg.putpixel((column, row), (0, 255, 0))
                counter = counter + 1
            index = index + 1

    return {
        'image': pil_to_base64(newImg),
        'percent': math.floor(counter / (w * h) * 100)
    }
