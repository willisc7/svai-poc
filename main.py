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
import requests
import datetime
import logging
import http.client as http_client

from collections import defaultdict
from google.cloud import storage
from google.cloud import vision
from google.cloud import bigquery
from google.cloud.bigquery import dataset

vision_client = vision.ImageAnnotatorClient()
storage_client = storage.Client()

def insert_into_dataset(project_id, route_dataset, route_table, json_str):
  bq_client = bigquery.Client(project=project_id)
  dataset_ref = bigquery.Dataset(
      dataset.DatasetReference(project_id, route_dataset))
  table = bq_client.get_table(
        dataset_ref.table(route_table))
  rows = [(json_str,)]
  errors = bq_client.insert_rows(table, rows)
  assert errors == []

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
    # todo: dont have the file open for 5 million years
    with open(local_json_filepath,'r+') as route_json_file:
        route_json_data = json.load(route_json_file)
        image_file_location = route_json_data["data"][0]["href"]
        print("Sending " + image_file_location + " to SVAI to extract item IDs from image")

        # Get access token to call SVAI API
        print("Acquiring access token")
        auth_url = ('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token')
        auth_req = requests.get(auth_url, headers={'Metadata-Flavor': 'Google'})
        auth_req.raise_for_status()
        access_token = auth_req.json()['access_token']
        # print('access_token: ', access_token)
        print("Access token acquired")

        # Call SVAI API
        print("Calling the SVAI API")
        svai_project_number = 903129578520
        url = ('https://aistreams.googleapis.com/v1alpha1/projects/'
               f'{svai_project_number}/locations/us-central1/'
               'clusters:predictShelfHealth?')

         # todo: loop through sample_data/image_metadata.json and process multiple images from the route
        data = json.dumps({
            "camera_id":"1001",
            "input_image": {
                "image_gcs_uri": "gs://route_images_02/82ca8d2495d0b4a0f643128f9391383a61ec39d48ea4101d994d422e7799bcad6ad34e303aff29ffa5455e935c18b92e9cc7767c0263e5655439b01c8317fa4f.jpg"
            },
            "config": {
                "processor_name": "projects/626086442885/locations/us/processors/1aac1c81b63cefc1",
                "price_tag_detection_model": "projects/617321834341/locations/us-central1/endpoints/2885725441702756352"
            },
            "analysis_type": "ANALYSIS_TYPE_PRICE_TAG_RECOGNITION"
        })
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        response = requests.post(url, headers=headers, data=data)
        response_metadata = {
            'json': response.json(),
            'time': datetime.datetime.now(),
        }
        print('Response json: ', json.dumps(response_metadata['json']))

        # Pull item IDs out of SVAI response
        print("Appending item IDs from SVAI response to original image metadata JSON")
        svai_response_dict = json.loads(json.dumps(response_metadata['json']),strict=False)
        items_dict = []
        for i in range(len(svai_response_dict["priceTags"])):
            items_dict.append(svai_response_dict["priceTags"][i]["entities"][0]["normalizedTextValue"])
        route_json_data["data"][0]["items"] = items_dict
        # delete test print
        route_json_file.seek(0)
        json.dump(route_json_data, route_json_file, indent = 4)
        print("Successfully appended item IDs to original image metadata JSON")

        # Upload JSON file to gs://route_results_02 to customer to consume
        # todo: read in result bucket from os.environ["RESULT_BUCKET"]
        results_bucket_name = "route_results_02"
        results_bucket = storage_client.get_bucket(results_bucket_name)
        blob = results_bucket.blob("test_route.json")
        # Test: print JSON file contents to logs
        # route_json_file.seek(0)
        # print(route_json_file.read())

        print("Saving result to gs://" + results_bucket_name + "/test_route.json")
        blob.upload_from_filename(local_json_filepath)
        print("File saved.")

        # Insert JSON into BQ
        project_id = 'cloud-store-vision-test'
        route_dataset = 'routes'
        route_table = 'test-data'
        route_json_str = json.dumps(route_json_data)
        insert_into_dataset(project_id, route_dataset, route_table, route_json_str)

    print("File {} processed.".format(filename))
