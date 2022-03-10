### Prerequisites

* Disable constraints/cloudfunctions.allowedIngressSettings org policy on the project
* Disable constraints/iam.disableServiceAccountKeyCreation org policy on the project
* Enable all the APIs https://console.cloud.google.com/flows/enableapi?apiid=cloudfunctions,cloudbuild.googleapis.com,pubsub,storage_api,vision.googleapis.com&redirect=https://cloud.google.com/functions/docs/tutorials/ocr&_ga=2.154163455.673635666.1645538540-966849366.1644425268
* Give default app engine svc acct owner privs (fix later but needs at least data editor for BQ insert)
* Used this as a guide: https://cloud.google.com/functions/docs/tutorials/ocr#functions_ocr_setup-python
* In BQ, create:
  * dataset named "routes"
  * table named "test-data"
  * schema in test-data table that has one field of type STRING called RouteData

### Setup

0. Create the bucket that will store the route images, the bucket that will receive the route metadata CSV and trigger the cloud function, and the bucket where the resulting JSON file containing the items found in the route pictures and their location will be stored
    ```
    gsutil mb gs://route_images_02
    gsutil mb gs://route_metadata_02
    gsutil mb gs://route_results_02
    ```
0. Upload images to `gsutil mb gs://route_images_02`
    ```
    gsutil cp 1.jpg gs://route_images_02
    gsutil cp 2.jpg gs://route_images_02
    gsutil cp 3.jpg gs://route_images_02
    ```
0. Deploy the image processing function with a Cloud Storage trigger and upload CSV to trigger it
```
gcloud functions deploy svai-extract \
--runtime python39 \
--trigger-bucket route_metadata_02 \
--entry-point process_image \
&& gsutil cp test_route.json gs://route_metadata_02
```

### Cleanup
`gcloud functions delete svai-extract`
