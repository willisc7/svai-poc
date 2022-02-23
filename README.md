### Prerequisites

* Disable constraints/cloudfunctions.allowedIngressSettings org policy on the project
* Disable constraints/iam.disableServiceAccountKeyCreation org policy on the project
* Enable all the APIs https://console.cloud.google.com/flows/enableapi?apiid=cloudfunctions,cloudbuild.googleapis.com,pubsub,storage_api,vision.googleapis.com&redirect=https://cloud.google.com/functions/docs/tutorials/ocr&_ga=2.154163455.673635666.1645538540-966849366.1644425268
* Give default app engine svc acct owner privs (fix later)
* Used this as a guide: https://cloud.google.com/functions/docs/tutorials/ocr#functions_ocr_setup-python

### Setup

0. Create the bucket that will store the route images `gsutil mb gs://route_images_00`
0. Create the bucket that will receive the route metadata CSV and trigger the cloud function `gsutil mb gs://route_metadata_00`
0. Create the bucket where the resulting JSON file containing the items found in the route pictures and their location will be stored `gsutil mb gs://route_results_00`
0. Deploy the image processing function with a Cloud Storage trigger and upload CSV to trigger it
```
gcloud functions deploy svai-extract \
--runtime python39 \
--trigger-bucket route_metadata_00 \
--entry-point process_image \
&& gsutil cp test_route.csv gs://route_metadata_00
```

### Cleanup
`gcloud functions delete svai-extract`
