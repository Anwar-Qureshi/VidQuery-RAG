import os
from dotenv import load_dotenv

# FastAPI Imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

# LangChain Imports for Phase 2
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Load our API keys from the .env file!
load_dotenv()

###Lines 1-4 (Imports): We are grabbing all our tools. 
# FastAPI is the server itself. CORSMiddleware handles security rules. 
# BaseModel handles making sure the data sent to us is formatted correctly. 
# Finally, we bring in the YouTube API tool.###

app = FastAPI(title="YouTube RAG API")
#This literally creates and starts the engine of your server. app is now your backend.

# Allow our Chrome Extension to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Fine for a local developer extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#Lines 9-16 (CORS): Cross-Origin Resource Sharing. Browsers have a strict security rule that says a website (like YouTube) cannot make a request to a totally different API (like your local server at port 8000). By doing this, we say "Hey Server, accept requests from anywhere (*)", which allows our future Chrome Extension to talk to it successfully.

# --- PHASE 2: GLOBAL VARIABLES ---
# In-memory dictionary to store our FAISS vector databases per video.
vector_stores = {}

# Initialize embeddings (HuggingFace) and LLM (Groq) once at startup to save time.
# all-MiniLM-L6-v2 is a very fast, free, open-source embedding model.
# llama-3.1-8b-instant is Meta's incredible open-source AI hosted by Groq.
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.2)


# Defines what JSON we expect mapped directly to a Python object
class TranscriptRequest(BaseModel):
    video_id: str
    transcript_text: str | None = None
#Lines 18-21 (Request Model): This is a blueprint. It tells the server: "When someone sends you data, I expect it to be a JSON object containing a key called video_id with a string value."

# New Request Model for Chatting
class ChatRequest(BaseModel):
    video_id: str
    question: str


# --- ENDPOINT 1: PROCESS VIDEO (Ingestion & Embedding) ---
@app.post("/api/process") 
async def process_video(req: TranscriptRequest):
    """
    Given a YouTube Video ID, runs locally to download the transcript, 
    splits it, embeds it into FAISS, and saves it in memory.
    """
    try:
        # If we already vectorized this video, skip processing!
        if req.video_id in vector_stores:
            return {"status": "success", "message": "Video already processed and ready."}

        # Step 1: Grab Transcript from Extension or Fallback to Python Script
        condensed_text = req.transcript_text

        # If the Chrome Extension couldn't extract it, use python Invincible Mode
        if not condensed_text or len(condensed_text) < 10:
            video_transcripts = YouTubeTranscriptApi().list(req.video_id)
            try:
                # First try finding manually created English transcripts
                transcript_list = video_transcripts.find_manually_created_transcript(["en", "en-US", "en-GB"]).fetch()
            except:
                try:
                    # If manual doesn't exist, fallback to auto-generated English
                    transcript_list = video_transcripts.find_generated_transcript(["en", "en-US", "en-GB"]).fetch()
                except:
                    # Last resort: grab whatever language is available and auto-translate to English!
                    fallback = [t for t in video_transcripts]
                    if not fallback:
                        raise Exception("Absolutely no transcripts exist for this video.")
                    transcript_list = fallback[0].translate('en').fetch()
            
            # We only want the text, not the timing data
            condensed_text = " ".join([chunk.text for chunk in transcript_list])
        
        # Step 2: Split the massive text into 1000-character chunks (LangChain)
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = [Document(page_content=condensed_text)]
        chunks = splitter.split_documents(docs)

        # Step 3: Embed chunks and save to a local FAISS Vector database (LangChain)
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # Save it to our global dictionary so the Chat endpoint can use it later
        vector_stores[req.video_id] = vector_store

        return {"status": "success", "message": f"Successfully ingested {len(chunks)} chunks into FAISS!"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- ENDPOINT 2: CHAT (Retrieval & Generation) ---
@app.post("/api/chat")
async def chat_with_video(req: ChatRequest):
    """
    Takes a question, searches the FAISS DB for relevant transcript chunks, 
    and sends them to the Groq LLM to generate an answer.
    """
    try:
        # Make sure the user ran /api/process first!
        if req.video_id not in vector_stores:
            raise HTTPException(status_code=404, detail="Error: Please process the video first before asking questions.")
        
        # Retrieve the relevant FAISS database
        vector_store = vector_stores[req.video_id]
        
        # Set up the Retriever to find the top 4 most relevant chunks
        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})

        # Define how the LLM should behave
        template = """
        You are a highly intelligent and helpful YouTube assistant. 
        Answer the user's question based strictly on the provided transcript context from the video.
        If the context does not contain the answer, gracefully state that the video doesn't cover that topic.

        Context:
        {context}

        Question: {question}
        """
        prompt = PromptTemplate.from_template(template)

        # Helper function to join the 4 retrieved chunks into one big string
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Build the magnificent LCEL Chain!
        # 1. Grab context and pass question -> 2. Insert into Prompt -> 3. Send to LLM -> 4. Output as String
        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        ###Takes the user's question.
        ###Passes the question to the FAISS retriever to find the top 4 chunks of the transcript that are most relevant to the question format them nicely (format_docs).
        ###Takes the retrieved context + the question and jams them into our instruction prompt.
        ###Passes the filled-out prompt to the llm (Groq/Llama-3).
        ###Parses the messy LLM JSON response into a clean, smooth English string (StrOutputParser).

        # Execute our chain!
        answer = chain.invoke(req.question)

        return {"status": "success", "answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Starts the server instantly on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
#Lines 52-55 (The Runner): This is the standard Python way to say "If this file is run directly (not imported), start the server." It uses uvicorn to launch the app on your local machine at port 8000.