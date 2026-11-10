# Serverless ML Workflow on AWS

An image classifier (bicycle vs motorcycle) deployed on SageMaker and wrapped in a Step Functions workflow that rejects low-confidence predictions.

## Results

| Item | Value |
|------|-------|
| Final validation accuracy (epoch 30 of 30) | 0.854 |
| Best validation accuracy (epoch 18) | 0.870 |
| Chance level for 2 balanced classes (epoch 1 validation accuracy) | 0.500 |
| Final training accuracy | 0.985 |
| Confidence threshold in the workflow | 0.67 |
| Captured endpoint calls (Model Monitor) | 23 records in 12 `.jsonl` files; 3 below the threshold (1 below 0.60, 2 between 0.60 and 0.67), 20 at 0.70 or above |

These are numbers from the training log and captured records in `starter.ipynb` and `captured_data/`. The validation set is the same as the test set (see Limitations).

## Problem

The fictional company Scones Unlimited wants to route delivery drivers by vehicle type. The task is to classify an image as a bicycle or a motorcycle and run it as a serverless workflow that fails loudly when the model is unsure.

## Data

CIFAR-100, downloaded from the University of Toronto. Only the `bicycle` (label 8) and `motorcycle` (label 48) classes are kept: 1,000 training images and 200 test images, 32x32 pixels, saved as PNGs and uploaded to S3.

## Approach

- ETL in the notebook: download, unpickle, filter to two classes, write PNGs, build `.lst` metadata files (`train.lst`, `test.lst`).
- Train with the SageMaker built-in image-classification algorithm (ResNet, 152 layers by default, SGD, learning rate 0.1, batch size 32, 30 epochs, 2 classes) on one `ml.p3.2xlarge`. Only image shape, class count and sample count were set; the rest are algorithm defaults.
- Deploy on one `ml.m5.xlarge` endpoint with Data Capture on, so each request and response is stored in S3 for Model Monitor.
- Three Lambda functions in `lambda.py`: serialize an S3 image to base64, call the endpoint, and filter on confidence. The filter raises an error if no class probability reaches 0.67.
- Step Functions chains the three Lambdas (`Scones.asl.json`); each step has a `Retry` block for transient Lambda errors, but none has a `Catch`, so a failure such as `THRESHOLD_CONFIDENCE_NOT_MET` fails the execution visibly.
- Plot captured confidence scores (a scatter against 0.94, the starter code's cut-off, and a histogram against the 0.67 threshold) to monitor the endpoint.

## Repo contents

| Path | Description |
|------|-------------|
| `starter.ipynb` | ETL, training, deployment, monitoring plots (with outputs) |
| `lambda.py` | Source of the three Lambda functions (filter corrected to match the deployed behaviour, see below) |
| `Scones.asl.json` | Step Functions state machine definition |
| `execution-detail.json` | One workflow execution |
| `captured_data/` | Model Monitor records from the endpoint |
| `test/`, `test.lst`, `train.lst` | Test images and SageMaker metadata files |
| `stepfunctions_graph.png`, `stepfunctions_graph (1).png`, `file.png` | Workflow screenshots and a sample CIFAR image |

![Step Functions graph](stepfunctions_graph.png)

## How to run

Notebook-only; there is no local script. It needs an AWS account.

1. Open `starter.ipynb` in SageMaker Studio (Python 3 kernel, `ml.t3.medium`) and run the cells in order.
2. Create three Lambda functions from `lambda.py` and set `ENDPOINT` in the classifier to your endpoint name.
3. Create a Step Functions state machine from `Scones.asl.json` (replace `<ACCOUNT_ID>` with your AWS account ID) and run it with input like `{"image_data": "", "s3_bucket": "<bucket>", "s3_key": "test/bicycle_s_001789.png"}`.
4. Delete the endpoint afterwards to stop charges.

## Note on lambda.py

`lambda.py` was corrected to match the deployed behaviour. The recorded classifier output in `execution-detail.json` is `{statusCode, body: '<JSON string>'}`, with `inferences` nested inside `body`. The earlier filter read a top-level `event['inferences']`, which would have raised a `TypeError` on that shape. The deployed filter was a separate file (`lambda_function.py`, where the `THRESHOLD_CONFIDENCE_NOT_MET` raise is at line 25 per the execution trace) that is not in this repo. The repo filter now parses `body` when present, keeps the 0.67 threshold, and still raises `THRESHOLD_CONFIDENCE_NOT_MET` if no class reaches it.

## Limitations and next steps

- The validation channel uses the same 200 images as the test set, so the accuracy figures are not a held-out estimate and are likely optimistic.
- Training accuracy (0.985) is well above validation (0.854), so the model overfits the 1,000 images. Data augmentation or more samples would help.
- Only 23 monitored requests were captured, too few to say anything reliable about confidence drift.
- The 0.67 threshold was not tuned against accuracy; it should be chosen from a precision/coverage trade-off.

Coursework for the Udacity AWS Machine Learning Engineer programme.
