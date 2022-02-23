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
import csv

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

    local_csv_filepath = "/tmp/test_route.csv"
    local_json_filepath = "/tmp/test_route.json"
    
    # Convert CSV to JSON and store both in /tmp
    # todo: do this in standalone function
    print("Downloading gs://" + bucket_name + "/" + filename + " to " + local_csv_filepath)
    metadata_bucket = storage_client.bucket(bucket_name)
    metadata_csv_blob = metadata_bucket.blob(filename)
    metadata_csv_blob.download_to_filename(local_csv_filepath)

    print("Converting " + local_csv_filepath + " to " + local_json_filepath)
    json_array = []
    with open(local_csv_filepath, encoding='utf-8') as csvf:
        csv_reader = csv.DictReader(csvf) 
        for row in csv_reader: 
            json_array.append(row)

    with open(local_json_filepath, 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(json_array, indent=4))

    print("Successfully converted " + local_csv_filepath + " to " + local_json_filepath)

    # Test: check JSON file contents
    # json_file = open(local_json_filepath, "r")
    # print(json_file.read())

    # For each JSON array index (which we assume is a route), send the
    # referenced image to SVAI to get back a list of item IDs found
    # in the image

    route_json_file = open(local_json_filepath, "r")
    route_json_content = route_json_file.read()
    route_json_object = json.loads(route_json_content)
    for i in range(len(route_json_object)):
        # todo: parallelize
        image_file = route_json_object[i]['Image file name']
        print("Sending " + image_file + " to SVAI to extract item IDs from image")
        # todo: append item IDs to JSON index
    
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
