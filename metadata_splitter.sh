#!/bin/bash
#
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
# 
# WARNING: this code was written for a proof of concept. Do not use in
# production. Reference code can be found here:
# https://cloud.google.com/functions/docs/tutorials/ocr#functions_ocr_setup-python
# 
# Why this script exists: JSON metadata files sometimes contain multiple
# image file references. The POC is designed to support one image file
# reference at a time. This is because event-based cloud function
# triggers have a max timeout of 10 minutes. Instead of putting an
# arbitrary image number limit on metadata JSON files we opted for
# assuming one imager per metadata JSON.

boilerplate_json=$(cat  << EOF
{
    "notificationId": "04ecadd0-6d84-47db-b08b-b2012d103e9c",
    "notificationTimestamp": "2022-03-28T14:17:16.689Z",
    "siteId": "98dcf2fa-4fa8-43ba-b6a4-8794f23b467d",
    "siteOwner": "35ecedf1-73a9-4490-90a3-f5b0363ffddc",
    "siteName": "Brain Lab",
    "data": []
}
EOF
)

dir_name=$(date "+%Y%m%d")
mkdir $dir_name
jq -c '.data[]' ./test/image_metadata.json | while read i; do
    output_filepath="$dir_name/$(echo $i | jq -r .hash).json"
    echo $boilerplate_json > $output_filepath
    echo $(jq ".data[0] |= . + $i" $output_filepath) > $output_filepath
done