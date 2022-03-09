curl --verbose -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json; charset=utf-8" https://autopush-aistreams.sandbox.googleapis.com/v1alpha1/projects/903129578520/locations/us-central1/clusters:predictShelfHealth -d '{ "camera_id":"1001", "input_image": {"image_gcs_uri": "gs://leyaliu_test/price_tag_test_001.jpg"}, "config": { "processor_name": "projects/626086442885/locations/us/processors/1aac1c81b63cefc1"}, "config": { "price_tag_detection_model": "projects/626086442885/locations/us-central1/endpoints/5284908192021610496"}, "analysis_type": "ANALYSIS_TYPE_PRICE_TAG_RECOGNITION"}'

def svai_api_caller(event, context):
  project_number = 903129578520
  dataset_name = 'albertsons_cds_captured_shelf_mixed_ocr_produce_meat_v4'
  image_path = f'gs://{event["bucket"]}/{event["name"]}'
  if image_path.endswith('.pb'):  # Don't process protobufs stored here.
    # Just internal. Not needed for albertsons.
    return
  camera_id = os.path.dirname(event['name'])
  image_metadata = {
      'gcs_uri': image_path,
      'camera_id': camera_id,
      'time': datetime.datetime.now()
  }
  print('Image path: ', image_path),

  # Authentication.
  auth_url = ('http://metadata.google.internal/computeMetadata/v1/instance/'
              'service-accounts/default/token')
  auth_req = requests.get(auth_url, headers={'Metadata-Flavor': 'Google'})
  auth_req.raise_for_status()
  access_token = auth_req.json()['access_token']
  print('access_token: ', access_token)

  # Request.
  print('Trying to run command.')
  url = ('https://aistreams.googleapis.com/v1alpha1/projects/'
         f'{project_number}/locations/us-central1/'
         'clusters:predictShelfHealth?')
  data = json.dumps({
      'camera_id': camera_id,
      'input_image': {
          'image_gcs_uri': image_path
      },
      'config': {
          'dataset_name': dataset_name
      }
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
  print('Ran command.')
  print('Response text: ', response.text)