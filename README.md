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
    gsutil -m cp ./sample_data/*.jpg gs://route_images_02
    ```
0. Deploy the image processing function with a Cloud Storage trigger
```
gcloud functions deploy svai-extract \
--runtime python39 \
--set-env-vars RESULTS_BUCKET=route_results_02 \
--trigger-bucket route_metadata_02 \
--entry-point process_image
```
0. Metadata is typically generated as a single JSON file. We need to split that into one JSON file per image because event-based cloud function triggers timeout after 10 minutes. Do the following to properly split the files:
    * Copy the JSON that looks like the following in the `image_metadata.json` accompanying the images to `metadata_splitter.sh`
        ```
        "notificationId": "some_value",
        "notificationTimestamp": "some_value",
        "siteId": "some_value",
        "siteOwner": "some_value",
        "siteName": "some_value",
        ```
    * In `metadata_splitter.sh` change the filepath on the line with the `jq` statement to point to `image_metadata.json`
    * In `image_metadata.json` find and replace all bucket names and file paths with `route_images_02`
    * Run the script: `./metadata_splitter.sh`
0. While the SVAI API is in alpha give it about 1 minute in between uploads to avoid 500 errors
```
for FILE in ./SOME_DATE/*.json; do gsutil cp $FILE gs://route_metadata_02; sleep 60; done
```

### Cleanup
`gcloud functions delete svai-extract`
