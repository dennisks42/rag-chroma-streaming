# mengalo-custom-extension-stream
Custom-extension streamed to WxA




## build it


* If you have a mac, then run commands :

```sh
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

* for win OS in powershell run
```sh
.\.venv\bin\activate
```


# Build and run a container

```sh
podman build -t blumareks/fastapi-stream:0.2.3 .

podman run -t -p 8000:8000 \                    
 -e WATSONX_IAM_APIKEY="put here IAM api key" \
 -e WATSONX_PROJECT_ID="put here wx.ai project id" \
 -e WATSONX_API_URL="https://us-south.ml.cloud.ibm.com or put other link" \
 -e CHROMA_URL="https://where is your chroma service/search" \
 -e RETRIVER="chroma" \
 -e CHROMA_FOR_WD_PROJECT="[{'chroma':'https://I think it is unused for now/search','WATSONX_PROJECT_ID':'I think it is unused for now' }]" \
 -e NUMBER_OF_RESPONSES_FOR_GENAI=2 \
 -e WATSONX_MODEL_ID="ibm/granite-8b-code-instruct" \
  --name fstream  blumareks/fastapi-stream:0.2.3

podman rm fstream 

```


## Quick test

```sh

curl --location 'http://127.0.0.1:8000/query-streamed' \
--header 'Content-Type: application/json' \
--data '{
	"query":"write about cleanses",
    "project_id": "c17ff424-cb8e-447f-8b95-c3db1639176f",
    "prompt" : "Rewrite the best answer from the listed answers for the question, rewrite the answer using the best listed answer using less than 30 words. Do not tell which answer it is",
    "model" : "mistralai/mixtral-8x7b-instruct-v01"
}'

```
