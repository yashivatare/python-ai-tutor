from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import sys
import os  # <-- NEW: To find files

# --- NEW LANGCHAIN IMPORTS ---
from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter

# --- Imports moved from 'langchain' to 'langchain_core' ---
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
# --- END NEW IMPORTS ---


# --- SETUP ---

# 1. Create our "Head Waiter"
app = FastAPI()

# 2. Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount static files directory for frontend assets (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Initialize our "AI Engine" (Ollama) and "Plumbing"
# This points to our local 'phi3' model
llm = ChatOllama(model="phi3")

# This is the "magic" that turns text into searchable numbers (vectors)
embeddings = OllamaEmbeddings(model="phi3")

# This will hold our "magic bookshelf" (the vector database)
# We set it to None for now. We will build it when the server starts.
vectorstore = None

# --- END SETUP ---


# --- API "ORDER FORMS" (BaseModels) ---

# Order form for the Code Executor
class CodeInput(BaseModel):
    source_code: str

# NEW: Order form for the AI Tutor
class QuestionInput(BaseModel):
    question: str

# --- END ORDER FORMS ---


# --- NEW: SERVER STARTUP EVENT ---
# This code runs ONCE when you start the server
# --- NEW: "SMART" SERVER STARTUP EVENT ---
# This version uses a "smart" splitter that understands Markdown headers
@app.on_event("startup")
def load_and_build_database():
    global vectorstore
    
    print("--- Server is starting up... ---")
    print("--- Loading knowledge base with 'Smart' Markdown Splitter... ---")
    
    knowledge_base_dir = "knowledge_base"
    
    # 1. Define the headers we want to "split" on
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    # 2. Create our new "smart" splitter
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    all_split_docs = [] # A list to hold all our new "pages"
    
    # 3. Loop through all .md files in the directory
    for filename in os.listdir(knowledge_base_dir):
        if filename.endswith(".md"):
            file_path = os.path.join(knowledge_base_dir, filename)
            
            # Load the raw text of the file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
            except Exception as e:
                print(f"--- FAILED to read {filename}: {e} ---")
                continue
            
            # 4. "Smart" split the file text based on its headers
            new_docs = markdown_splitter.split_text(file_content)
            
            # 5. Add "source" metadata to each new chunk so we know where it came from
            for doc in new_docs:
                doc.metadata["source"] = filename
            
            # 6. Add the new "pages" to our master list
            all_split_docs.extend(new_docs)

    if not all_split_docs:
        print("!!! No documents found in 'knowledge_base'. AI Tutor may not work. !!!")
        return

    # 7. Build the "Magic Bookshelf" (ChromaDB) with our new "smart" pages
    print(f"--- Building 'magic bookshelf' with {len(all_split_docs)} new 'smart' pages... ---")
    vectorstore = Chroma.from_documents(
        documents=all_split_docs, 
        embedding=embeddings
    )
    print("--- 'Magic bookshelf' is ready. ---")
    print("--- Server is ready to accept requests. ---")


# --- END STARTUP EVENT ---


# --- API ENDPOINTS ---

# Endpoint 1: The "Front Door" - Serve the frontend
@app.get("/")
def read_root():
    """Serve the frontend HTML file"""
    return FileResponse("static/index.html")


# Endpoint 2: The "Test Kitchen" (Code Executor)
# Endpoint 2: The "Test Kitchen" (Code Executor) - NOW WITH AI DEBUGGING!
@app.post("/run_code")
def run_code(code_input: CodeInput):
    
    # 1. Get both pieces of data from the "order form"
    code = code_input.source_code
    
    try:
        # 2. Run the code in the "secure back room"
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        # 3. If it works, return "Accepted" as normal
        return {
            "status": "Accepted",
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    # 4. --- NEW AI DEBUGGER LOGIC ---
    # We will catch both types of errors and handle them
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        
        # 5. Figure out what the error message was
        error_message = ""
        status = ""
        if isinstance(e, subprocess.TimeoutExpired):
            status = "Time Limit Exceeded"
            error_message = "Your code took more than 5 seconds to run and was stopped."
        else: # It must be a CalledProcessError
            status = "Runtime Error"
            error_message = e.stderr # The actual error from Python
        
        print(f"--- Code failed: {status}. Asking AI for a fix... ---")
            
        # 6. Create a "Debug" prompt template
        debug_template = """
        You are an expert Python debugger and friendly tutor.
        A student's code failed.

        STUDENT'S CODE:
        {code}
        
        THE ERROR:
        {error}

        Please do the following:
        1. **Try to infer the student's *intent***. What problem do you think they were trying to solve?
        2. Based on your guess, explain the bug in a simple, friendly tone.
        3. Provide the corrected, complete Python code that matches your inferred intent.
        """
        
        debug_prompt = ChatPromptTemplate.from_template(debug_template)
        
        # 7. Create a simple "Debug Chain"
        # We don't need our RAG retriever here, we are just asking the AI to fix it.
        debug_chain = (
            debug_prompt
            | llm
            | StrOutputParser()
        )

        # 8. Run the chain with all our context
        ai_fix = debug_chain.invoke({
            "code": code,
            "error": error_message
        })

        # 9. Return the original error *plus* the new AI-generated fix
        return {
            "status": status,
            "stdout": e.stdout if hasattr(e, 'stdout') else "", # Show original output
            "stderr": error_message, # Show original error
            "ai_fix": ai_fix # Add the new AI fix
        }
    
    
# --- NEW: ENDPOINT 3 ---
# The "AI Brain" (Tutor)
@app.post("/ask_tutor")
def ask_tutor(question_input: QuestionInput):
    global vectorstore
    
    if vectorstore is None:
        return {"error": "Knowledge base is not loaded. Did you add files to the 'knowledge_base' folder?"}
    

    question = question_input.question
    

    # 1. Create a "retriever"
    # This is a tool that "retrieves" pages from our "magic bookshelf"
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # k=1 means "get the 1 best page"

    retrieved_docs = retriever.invoke(question)

    print(retrieved_docs)

    # 2. Define the "Prompt Template" (The AI's Instructions)
    # This is the most important part. We tell the AI *how* to behave.
    # 2. Define the "Prompt Template" (The AI's Instructions)
    template = """
    You are a friendly, engaging, and Socratic Python tutor.
    You have two modes: "Tutoring Mode" and "Conversational Mode".

    ---
    **Mode 1: Conversational Mode**
    If the user's question is NOT related to Python or the "CONTEXT" (e.g., they say "hi", "hello", "thanks", "how are you", or "who are you?"), 
    then **IGNORE THE CONTEXT COMPLETELY**. 
    Just have a normal, friendly, one or two-sentence conversation. 
    Do NOT ask a follow-up question in this mode.

    ---
    **Mode 2: Tutoring Mode**
    If the user's question IS about Python and related to the "CONTEXT", you must follow these rules:
    
    1. Your job is to answer the user's question based ONLY on the context provided below.
    2. The user must never know where the information comes from — treat the context as your internal knowledge.
    3. Begin by clearly explaining the concept, using only the provided context.
    4. If the user’s question includes words like "analogy", "example", or "metaphor",
       include a simple real-world analogy to make the explanation easier to understand.
    5. Adapt your response to the user’s intent:
       - If the question is about how to begin learning Python, how to progress, or what topics to study next,
         explain the learning journey from beginner to advanced based on the context.
       - If the question is about Python fundamentals (such as print(), variables, loops, basic syntax, or simple programs),
         break down the concepts with clear, beginner-friendly examples.
    6. Always end your response with ONE follow-up question or a small coding challenge to check understanding.
    7. Keep your explanations concise, friendly, and encouraging.
    
    ---
    CONTEXT:
    {context}
    
    USER'S QUESTION:
    {question}
    
    YOUR RESPONSE:
    """
    prompt = ChatPromptTemplate.from_template(template)

    prompt = ChatPromptTemplate.from_template(template)

    # 3. Create the "Chain" (The "Plumbing" Assembly Line)
    # This is the "plumbing" that connects all our tools.
    # It says, "When a question comes in...
    # 1. Pass the question to the 'retriever' to get the 'context'.
    # 2. Pass the 'question' and 'context' to the 'prompt'.
    # 3. Pass the formatted 'prompt' to the 'llm' (Ollama).
    # 4. 'Parse' the 'output' into a simple string."
    
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 4. Run the chain!
    
    answer = chain.invoke(question)

    
    
    return {"answer": answer}

# --- END API ENDPOINTS ---