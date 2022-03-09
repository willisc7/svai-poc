# Copyright 2018, Google, LLC.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# WARNING: this code was written for a proof of concept. Do not use in
# production. Reference code can be found here:
# https://cloud.google.com/functions/docs/tutorials/ocr#functions_ocr_setup-python

import json
import os

from collections import defaultdict
from google.cloud import storage
from google.cloud import vision

vision_client = vision.ImageAnnotatorClient()
storage_client = storage.Client()

def process_image(event, context):
    """Background Cloud Function to be triggered by Cloud Storage.
       This generic function logs relevant data when a file is changed.
    Args:
        event (dict):  The dictionary with data specific to this type of event.
                       The `data` field contains a description of the event in
                       the Cloud Storage `object` format described here:
                       https://cloud.google.com/storage/docs/json_api/v1/objects#resource
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None; the output is written to Stackdriver Logging
    """

    bucket_name = event['bucket']
    filename = event['name']

    # Download route JSON and store at path in local_json_filepath
    local_json_filepath = "/tmp/test_route.json"
    print("Downloading gs://" + bucket_name + "/" + filename + " to " + local_json_filepath)
    metadata_bucket = storage_client.bucket(bucket_name)
    metadata_json_blob = metadata_bucket.blob(filename)
    metadata_json_blob.download_to_filename(local_json_filepath)
    print("Successfully downloaded " + local_json_filepath)

    # Test: print JSON file contents to logs
    # todo: dump to string and replace newlines with spaces
    # with open(local_json_filepath, "r") as json_file:
    #     print(json_file.read())

    # Send the referenced image to SVAI to get back a list of item IDs found 
    # in the image and update file at local_json_filepath
    with open(local_json_filepath,'r+') as route_json_file:
        route_json_data = json.load(route_json_file)
        image_file_location = route_json_data["data"][0]["href"]
        print("Sending " + image_file_location + " to SVAI to extract item IDs from image")

        # Placeholder: SVAI API call happens here
        # Temp: sample SVAI response string JSON
        svai_response_string = '''
        {
          "priceTags": [
            {
              "priceTagBox": {
                "boundingBox": {
                  "xMin": 0.84018904,
                  "xMax": 0.9973369,
                  "yMin": 0.65774584,
                  "yMax": 0.735467
                },
                "detectionScore": 0.9999897,
                "mid": "price_tag",
                "objectClass": "price_tag"
              },
              "priceTagText": "244236\nTIDE FREE LIQ HE ORG 208 OZ 15\ndle\n",
              "entities": [
                {
                  "type": "number",
                  "mentionText": "244236",
                  "confidence": 1,
                  "region": {
                    "xMin": 0.24053451,
                    "xMax": 0.8285078,
                    "yMin": 0.3160763,
                    "yMax": 0.48501363
                  },
                  "normalizedTextValue": "244236"
                }
              ]
            },
            {
              "priceTagBox": {
                "boundingBox": {
                  "xMin": 0.76975274,
                  "xMax": 0.8773764,
                  "yMin": 0.23598571,
                  "yMax": 0.2728851
                },
                "detectionScore": 0.99998236,
                "mid": "price_tag",
                "objectClass": "price_tag"
              },
              "priceTagText": "266057\nPREPACK 2 BERKLEY JENSEN FL\n",
              "entities": [
                {
                  "type": "number",
                  "mentionText": "266057",
                  "confidence": 1,
                  "region": {
                    "xMin": 0.1325,
                    "xMax": 0.8575,
                    "yMin": 0.20588236,
                    "yMax": 0.44607842
                  },
                  "normalizedTextValue": "266057"
                }
              ]
            },
            {
              "priceTagBox": {
                "boundingBox": {
                  "xMin": 0.3351111,
                  "xMax": 0.43150008,
                  "yMin": 0.1437522,
                  "yMax": 0.16703528
                },
                "detectionScore": 0.9873115,
                "mid": "price_tag",
                "objectClass": "price_tag"
              },
              "priceTagText": "9860\n",
              "entities": [
                {
                  "type": "number",
                  "mentionText": "9860",
                  "confidence": 1,
                  "region": {
                    "xMin": 0.0776699,
                    "xMax": 0.5291262,
                    "yMin": 0.31318682,
                    "yMax": 0.47802198
                  },
                  "normalizedTextValue": "9860"
                }
              ]
            }
          ]
        }
        '''
        svai_response_dict = json.loads(svai_response_string,strict=False)
        items_dict = []
        for i in range(len(svai_response_dict["priceTags"])):
            items_dict.append(svai_response_dict["priceTags"][i]["entities"][0]["normalizedTextValue"])
        route_json_data["data"][0]["items"] = items_dict
        route_json_file.seek(0)
        json.dump(route_json_data, route_json_file, indent = 4)

        # Test: print JSON file contents to logs
        # route_json_file.seek(0)
        # print(route_json_file.read())

    # $ curl --verbose -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json; charset=utf-8" https://aistreams.googleapis.com/v1alpha1/projects/903129578520/locations/us-central1/clusters:predictShelfHealth -d '{ "camera_id":"1001", "input_image": {"image_gcs_uri": "gs://leyaliu_test/price_tag_test_001.jpg"}, "config": { "processor_name": "projects/626086442885/locations/us/processors/1aac1c81b63cefc1"}, "config": { "price_tag_detection_model": "project }
    
    # Upload JSON file to gs://route_results_00 to customer to consume
    # todo: read in result bucket from os.environ["RESULT_BUCKET"]
    results_bucket_name = "route_results_00"
    results_bucket = storage_client.get_bucket(results_bucket_name)
    blob = results_bucket.blob("test_route.json")
    
    # todo: insert JSON to BQ
    # todo: query with Looker

    print("Saving result to gs://" + results_bucket_name + "/test_route.json")

    blob.upload_from_filename(local_json_filepath)

    print("File saved.")

    print("File {} processed.".format(filename))
