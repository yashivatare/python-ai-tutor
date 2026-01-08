from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import sys
import os


from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="static"), name="static")


llm = ChatOllama(model="phi3")

embeddings = OllamaEmbeddings(model="phi3")

vectorstore = None


class CodeInput(BaseModel):
    source_code: str


class QuestionInput(BaseModel):
    question: str


@app.on_event("startup")
def load_and_build_database():
    global vectorstore

    print("--- Server is starting up... ---")
    print("--- Loading knowledge base with 'Smart' Markdown Splitter... ---")

    knowledge_base_dir = "knowledge_base"

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on)

    all_split_docs = []
    for filename in os.listdir(knowledge_base_dir):
        if filename.endswith(".md"):
            file_path = os.path.join(knowledge_base_dir, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
            except Exception as e:
                print(f"--- FAILED to read {filename}: {e} ---")
                continue

            new_docs = markdown_splitter.split_text(file_content)

            for doc in new_docs:
                doc.metadata["source"] = filename

            all_split_docs.extend(new_docs)

    if not all_split_docs:
        print("!!! No documents found in 'knowledge_base'. AI Tutor may not work. !!!")
        return

    print(
        f"--- Building 'magic bookshelf' with {len(all_split_docs)} new 'smart' pages... ---")
    vectorstore = Chroma.from_documents(
        documents=all_split_docs,
        embedding=embeddings
    )
    print("--- 'Magic bookshelf' is ready. ---")
    print("--- Server is ready to accept requests. ---")


@app.get("/")
def read_root():
    """Serve the frontend HTML file"""
    return FileResponse("static/index.html")


@app.post("/run_code")
def run_code(code_input: CodeInput):

    code = code_input.source_code

    try:
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        return {
            "status": "Accepted",
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:

        error_message = ""
        status = ""
        if isinstance(e, subprocess.TimeoutExpired):
            status = "Time Limit Exceeded"
            error_message = "Your code took more than 5 seconds to run and was stopped."
        else:
            status = "Runtime Error"
            error_message = e.stderr

        print(f"--- Code failed: {status}. Asking AI for a fix... ---")

        debug_template = """
        You are an expert Python debugger and friendly tutor.
        A student's code failed.

        STUDENT'S CODE:
        {code}
        
        THE ERROR:
        {error}

        Please do the following:
        1. Based on your guess, explain the bug in a simple, friendly tone.
        2. Provide the corrected, complete Python code that matches your inferred intent.
        """

        debug_prompt = ChatPromptTemplate.from_template(debug_template)

        debug_chain = (
            debug_prompt
            | llm
            | StrOutputParser()
        )

        ai_fix = debug_chain.invoke({
            "code": code,
            "error": error_message
        })

        return {
            "status": status,
            "stdout": e.stdout if hasattr(e, 'stdout') else "",
            "stderr": error_message,
            "ai_fix": ai_fix
        }


@app.post("/ask_tutor")
def ask_tutor(question_input: QuestionInput):
    global vectorstore

    if vectorstore is None:
        return {"error": "Knowledge base is not loaded. Did you add files to the 'knowledge_base' folder?"}

    question = question_input.question

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 3})  # k=1 means "get the 1 best page"

    retrieved_docs = retriever.invoke(question)

    print(retrieved_docs)

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
    6. Always end your response with ONE follow-up question.
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

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke(question)

    return {"answer": answer}
