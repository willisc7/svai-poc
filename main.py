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
bq_client = bigquery.Client()

def process_image(event, context):
    bucket_name = event['bucket']
    filename = event['name']

    # Download route JSON and store at path in local_json_filepath
    local_json_filepath = "/tmp/test_route.json"
    print("Downloading gs://" + bucket_name + "/" + filename + " to " + local_json_filepath)
    metadata_bucket = storage_client.bucket(bucket_name)
    metadata_json_blob = metadata_bucket.blob(filename)
    metadata_json_blob.download_to_filename(local_json_filepath)
    print("Successfully downloaded " + local_json_filepath)

    # Get access token to call SVAI API
    print("Acquiring access token")
    auth_url = ('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token')
    auth_req = requests.get(auth_url, headers={'Metadata-Flavor': 'Google'})
    auth_req.raise_for_status()
    access_token = auth_req.json()['access_token']
    # print('access_token: ', access_token)
    print("Access token acquired")

    # Send the referenced image to SVAI to get back a list of item IDs found 
    # in the image and update file at local_json_filepath
    with open(local_json_filepath,'r') as route_json_file:
        route_json_data = json.load(route_json_file)
    
    for item in route_json_data["data"]:
        image_file_location = item["href"]
        print("Sending " + image_file_location + " to SVAI to extract item IDs from image")

        # Call SVAI API
        print("Calling the SVAI API")
        svai_project_number = 903129578520
        url = ('https://aistreams.googleapis.com/v1alpha1/projects/'
                f'{svai_project_number}/locations/us-central1/'
                'clusters:predictShelfHealth?')

        data = json.dumps({
            "camera_id":"1001",
            "input_image": {
                "image_gcs_uri": image_file_location
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

        # Pull item IDs out of SVAI response and add them to the route JSON
        print("Appending item IDs from SVAI response to original image metadata JSON")
        svai_response_dict = json.loads(json.dumps(response_metadata['json']),strict=False)
        items_dict = []
        for i in range(len(svai_response_dict["priceTags"])):
            items_dict.append(svai_response_dict["priceTags"][i]["entities"][0]["normalizedTextValue"])
        item["items"] = items_dict

    # results JSON file must all be on one line in order for BQ autodetect
    # schema to work
    route_json_file = open(local_json_filepath, 'w')
    route_json_str = json.dumps(route_json_data)
    route_json_file.write(route_json_str)
    route_json_file.close()
    print("Successfully appended item IDs to original image metadata JSON")

    # Upload JSON file to gs://route_results_02 to customer to consume
    # todo: read in result bucket from os.environ["RESULT_BUCKET"]
    results_bucket_name = "route_results_02"
    results_bucket = storage_client.get_bucket(results_bucket_name)
    blob = results_bucket.blob("test_route.json")
    print("Saving result to gs://" + results_bucket_name + "/test_route.json")
    blob.upload_from_filename(local_json_filepath)
    print("File saved.")

    # Insert results JSON to BQ
    table_id = "cloud-store-vision-test.routes.test-data"
    job_config = bigquery.LoadJobConfig(
        autodetect=True, source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    )
    uri = "gs://" + results_bucket_name + "/test_route.json"
    load_job = bq_client.load_table_from_uri(
        uri, table_id, job_config=job_config
    )  # Make an API request.
    load_job.result()  # Waits for the job to complete.
    destination_table = bq_client.get_table(table_id)
    print("Loaded {} rows.".format(destination_table.num_rows))

    print("File {} processed.".format(filename))
