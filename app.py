from urllib import request
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Model, ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods
from dotenv import load_dotenv

import os
import http.client #token
import json #token
import requests #chroma
import time #measuring the time

load_dotenv()  # take environment variables from .env.

# load the environment variables
# get the IAM API Key from the environment variable    
iam_api_key = os.environ["WATSONX_IAM_APIKEY"]
#print(f"iam api key: {iam_api_key}")

watsonx_project_id = os.environ["WATSONX_PROJECT_ID"]
api_url = os.environ["WATSONX_API_URL"]
model_id = os.environ["WATSONX_MODEL_ID"]


number_of_responses_for_genai = int(os.environ["NUMBER_OF_RESPONSES_FOR_GENAI"])
retriver_discovery_or_chroma = os.environ["RETRIVER"]
json_chroma_for_wd_project = os.environ["CHROMA_FOR_WD_PROJECT"]

retriver_chroma_url = os.environ["CHROMA_URL"]

generate_params = {
    GenParams.MAX_NEW_TOKENS: 1000,
    GenParams.DECODING_METHOD: "greedy",
    GenParams.REPETITION_PENALTY: 1,
    GenParams.STOP_SEQUENCES: ["\\n\\n"]
}

watsonx_project_id=os.environ["WATSONX_PROJECT_ID"]

credentials=Credentials(
    api_key = iam_api_key, #WX_API_KEY,
    url = api_url #IBM_CLOUD_URL
    )
#print(credentials)

client=APIClient(credentials)
client_project = APIClient(credentials, project_id = watsonx_project_id)

MODEL_ID = model_id #"ibm/granite-8b-code-instruct" #"mistralai/mixtral-8x7b-instruct-v01"

# Initialize the app and add CORS middleware
app = FastAPI()
#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=['*'],
#    allow_credentials=True,
#    allow_methods=['*'],
#    allow_headers=["*"]
#)


# code that connects to chromaDB API service per project;
def retrive_chroma(query, project_id):


    #select the container to ping
    url = retriver_chroma_url

    # pick the url by project_id use-case

    print("in retriver")
    # connect to the container
    #print(query)
    # get results
    try:
        payload = json.dumps({
            "query": query,
            "no_results": number_of_responses_for_genai
        })
        headers = {
            "Content-Type":"application/json"
        }
        #print(payload)
        #print(headers)
        response = requests.request("POST", url, headers=headers, data=payload, verify=False)

        #print(response.text)

        result = response.text
    except Exception as e:
        return {'error': str(e)}

    return result 

# code that adds an original query to the received top 3 answers and sends the data to watsonx.ai with the custom prompt
def augment_chroma(query, response_retriver):
    #check if there are any answers, if no return empty
    #{"results":{"data":null,"distances":[[0.29149818420410156,0.6023381948471069]],"documents":[["Cleanses are a pack of specific juices that are particularly picked to help the customer with a specific health problem or improve their specific health category.","list the juices and lemonades in the order provided above. - Recommend drinking water or tea between juices or lemonades. - For the Gut Whisperer cleanse, start the first juice at 8 AM and the last lemonade at 8 PM. - The Gut Whisperer cleanse is a specialty cleanse; find it by searching \"gut whisperer well juicery\" and visiting the Well Juicery website. - For other questions, refer to the guide on the Well Juicery website for detailed instructions on consuming the cleanses."]],"embeddings":null,"ids":[["id19","id28"]],"included":["metadatas","documents","distances"],"metadatas":[[{"question":"**Cleanses:**"},{"question":"If asked about the order of taking the cleanses,"}]],"uris":null}}
    print("response from retriver")
    #print (response_retriver)
    if response_retriver is None:
        return
    
    # TODO select top three or n
    # Add the original query to the received top 3 answers

    # Extract the answer and source from the query result
    answer = []
    source = []
    i = 0
    response_json=json.loads(response_retriver)
    for passage in response_json['results']['documents'][0]:
        #print(passage)
        if i < number_of_responses_for_genai :
            text1 = passage#[i]
            #print(f"text1 index {i}")
            #print(text1)
            question_json = response_json['results']['metadatas'][0][i]
            text2 = question_json["question"]
            found_answer= text2 + text1
            answer.append(found_answer)
            source.append(response_json['results']['ids'][0][i])#passage['document_id'])
        i=i+1
        print(f"counter: {i}")

    # Return the answer, and source in a JSON response
    
    # TODO reprioritize using some strategy
    # TODO add query to the response
    print(answer)
    return {
        'answer': answer,
        'source': source
    }


#suggested filter
# sample output
# {'model_id': 'ibm/granite-8b-code-instruct', 'model_version': '1.1.0', 'created_at': '2024-10-31T19:14:17.242Z', 'results': [{'generated_text': '\n', 'generated_token_count': 1, 'input_token_count': 0, 'stop_reason': 'not_finished'}]}

async def event_stream(watonsx_model: Model, llm_input, citation):
    start_gen_time = time.perf_counter()
    count = 0
    # async for chunk in watonsx_model.generate_text_stream(prompt=llm_input, raw_response=True):
    for chunk in watonsx_model.generate_text_stream(prompt=llm_input, raw_response=True):
        json_data = json.dumps(chunk)
        print(chunk)

        if count == 0:
            duration = int((time.perf_counter() - start_gen_time)*1000)
            print(f"Time taken for FIRST TOKEN: {duration}")
        count += 1

        if citation is not None and chunk["results"][0]["stop_reason"] == "eos_token":
            duration = int((time.perf_counter() - start_gen_time)*1000)
            print(f"Time taken for last token: {duration}")
            chunk["results"][0]["generated_text"] += citation
            json_data = json.dumps(chunk)

        yield f"data: {json_data}\n\n"  # SSE format



@app.get("/")
async def root():
    return {"message": "Hello Mengalo Streaming"}

@app.post('/query-streamed')
async def stream_response(request:Request):
    payload_data = await request.json()
    prompt = payload_data["prompt"].strip()
    my_model = payload_data["model"].strip()
        
    try:         
        query = payload_data["query"].strip()
        #model = ModelInference(
        model = Model(
            model_id = my_model, 
            params = generate_params, 
            credentials = credentials,
            project_id = watsonx_project_id #WX_PROJECT_ID
        )
        ### start here

        print("in query method")
        #data = request.get_json()
        #if data is None:
        #    return {"error": "Invalid request, JSON expected"}, 400
        #query = data.get("query")
        #project = query = payload_data["project_id"].strip()
        #if query is None or project is None:
        #    return {"error": "Missing query or project"}, 400
        
        ### get chroma
        # select chroma vs watson
        start_retriver_time = time.perf_counter()
        match retriver_discovery_or_chroma:
            #case "discovery": 
            #    response_retriver = retrive(query, project)
            #    response_augmenter = augment(query, response_retriver)
            case "chroma":
                print("in case chroma")
                response_retriver = retrive_chroma(query, watsonx_project_id)
                response_augmenter = augment_chroma(query, response_retriver)
            # use just the text of the document placed in the filesystem
            case _:
                response_retriver = retrive_chroma(query, watsonx_project_id)
                response_augmenter = augment_chroma(query, response_retriver)

        stop_retriver_time = time.perf_counter()
        retriver_elapsed_time = int((stop_retriver_time - start_retriver_time)*1000)
        print(f"retrived in: {retriver_elapsed_time} ms")
        #print(response_augmenter)

        url = api_url
        i = 0
        responses = ""
        for i in range(len(response_augmenter["answer"])):

            responses = responses + f"answer {i+1}: "+ "".join(response_augmenter["answer"][i]) + "source: "+ response_augmenter["source"][i] +"\n"
        print("my responses**********")
        print(responses)
        genai_prompt = f"You are a knowledge worker.  You received the following question:\n{query}\n"
        genai_prompt2 = f"these are the answers from the knowledge retriever:\n {responses}\n"
        genai_prompt3_1 = """\n For example. The User asks the following question: 
        'tell me about green juice'; 
        the expected answer: 
        ' Our green juice is the WELL GREENS because of its name.  This are the details  on this particular juice - A 6-pack priced at $41.94, with ingredients including apple juice, spinach juice, kale juice, celery juice, lemon juice, and ginger juice 120 calories.'"""
        
        genai_prompt4 = f"""
            You are an AI assistant responsible for answering customer queries accurately and efficiently. You have access to a knowledge retrieval system that provides answers based on a database of pre-approved responses. 

            Your task is to respond to the following customer inquiry:
            Customer Inquiry:

            Consider the following details when crafting your response:
            - Ensure the response is clear, informative, and addresses the customer's specific question or concern.
            - If the query is about a product, include details like product name, description, benefits, ingredients, pricing, and any other relevant specifications.
            - If the query is about a service or general information, provide clear and concise details about the service, its features, or how to proceed with it.
            - Use an empathetic and helpful tone. Make sure the response feels personalized and offers useful insights, solutions, or next steps.

            Be mindful of the following:
            - If the query asks for a product’s nutritional information, provide specific ingredients, calories, and any additional details on benefits.
            - If the query is about payment or shipping, ensure the response is clear, addressing the process and providing any relevant instructions.
            - If the customer asks for more general information about your company, focus on values, mission, or product ranges.
            - If the query is about an issue (e.g., expired products, poor service), offer clear solutions such as refunds, replacements, or escalation to specialists if needed.

            Now, use the following responses from the knowledge retriever as a guide to help you craft your response:"""

        genai_prompt3 = f"{prompt}\n Answer only with the retrieved facts, don't make up an answer. If you don't know the answer - say that you don't know the answer."
        

        new_prompt = genai_prompt+genai_prompt2+genai_prompt3_1+genai_prompt3+genai_prompt4

        return StreamingResponse(event_stream (model, new_prompt, ""), media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Exception occurred: " + str(e))
    
    
