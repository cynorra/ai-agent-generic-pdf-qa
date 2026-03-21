AI-Powered Business Assistant (Generic AI Agent)

This project is an AI-powered assistant designed to help any type of business (restaurants, clinics, salons, consulting services, etc.) automatically learn its operational rules from PDF documents and interact with customers in natural language to take orders and schedule appointments.

The system is built using Google’s advanced Gemini infrastructure combined with modern RAG (Retrieval-Augmented Generation) and LangGraph-based orchestration.

🚀 Key Features

Business-Agnostic Architecture (Generic):
No hardcoded rules exist in the system. All business data such as menus, tax rates, working hours, appointment durations, and delivery fees are automatically extracted from uploaded PDFs using Gemini-powered information extraction.

Advanced Memory & Decision-Making (LangGraph):
The assistant understands user intent (order, appointment, or general inquiry), maintains conversation context (session memory), and responds accordingly.

Dynamic RAG Module:
When users ask questions about the business, the system retrieves accurate answers directly from the PDF using a FAISS vector database, minimizing hallucinations.

Built-in Tools:
The AI can update carts, calculate totals, and write directly to the database when needed.

Portable Database:
Uses SQLite for simplicity and easy deployment, eliminating the need for a cloud database.

🛠 Tech Stack

Backend Framework: FastAPI (Python)

AI/LLM: Google Gemini (1.5 Flash) & Gemini Embeddings

Orchestration: LangChain & LangGraph

Vector Database: FAISS

Relational Database: SQLite

Logging: Structlog

📦 Installation

Install Python
Make sure Python 3.10 or higher is installed on your system.

Install Dependencies
Run the following command in the project directory:

pip install -r requirements.txt

Set API Key (Environment Variables)

Open the .env.example or .env file in the root directory.

Replace the GOOGLE_API_KEY value with your own Gemini API key.

Example:

GOOGLE_API_KEY=AIzaSyA...
⚙️ Running the System

You can start the system easily using:

run_system.bat

Or directly via terminal:

uvicorn app.main:app --host 0.0.0.0 --port 5000

Once running, you can access the API documentation at:
http://localhost:5000/docs

📚 Usage Workflow

The system operates in two main steps:

1. Register a Business

Upload a business-specific PDF via the /business/load_pdf endpoint.

During upload:

The document is chunked

Converted into embeddings

Stored in a FAISS vector database

Business rules are extracted and saved as structured JSON

2. Chat Interaction

After setup, send messages to /agent/chat with:

session_id

business_name

The assistant will respond based on the business capabilities and complete actions such as answering questions, taking orders, or scheduling appointments.

🔒 Security Notes

API Key Protection:
Your Google API key is stored in the .env file. Ensure it is kept secure and never exposed in public repositories. Always remove sensitive data before sharing the source code.

📄 License & Ownership

This architecture is designed as a scalable and commercially viable solution.
It can be customized and integrated into different businesses as a reusable AI infrastructure.
