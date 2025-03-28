## SERIALIZER LAMBDA FUNCTION
import json
import boto3
import base64

s3 = boto3.client('s3')

def lambda_handler(event, context):
    key = event['s3_key']
    bucket = event['s3_bucket']

    s3.download_file(bucket, key, '/tmp/image.png')

    with open('/tmp/image.png', 'rb') as f:
        im_data = base64.b64encode(f.read()).decode('utf-8')
    return {
        'statusCode': 200,
        'body': {
            'image_data': im_data,
            's3_bucket' : bucket,
            's3_key' : key,
            'inferences' : []
        }
    }

## CLASSIFICATION LAMBDA FUNCTION
import json
import sagemaker
import base64
from sagemaker.serializers import IdentitySerializer


ENDPOINT = "image-classification-2025-03-28-10-12-03-048"

def lambda_handler(event, context):

   
    image = base64.b64decode(event['body']['image_data']) 

    
    predictor = sagemaker.predictor.Predictor(
        endpoint_name=ENDPOINT,
        sagemaker_session=sagemaker.Session()
    )

    
    predictor.serializer = IdentitySerializer("image/png")
    
    
    inferences = predictor.predict(image)
    
  
    event["inferences"] = inferences.decode('utf-8')
    return {
        'statusCode': 200,
        'body': json.dumps(event)
    }
## FILTER THRESHOLD LAMBDA FUNCTION
import json

THRESHOLD = 0.67

def lambda_handler(event, context):
    inferences = event.get("inferences")
    
    if isinstance(inferences, str):
        inferences = json.loads(inferences)

    meets_threshold = any(confidence >= THRESHOLD for confidence in inferences)

    if meets_threshold:
        return {
            'statusCode': 200,
            'body': json.dumps(event)
        }
    else:
        
        raise Exception("THRESHOLD_CONFIDENCE_NOT_MET")