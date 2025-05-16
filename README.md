🏗️ BIM RAG System 🤖
A Retrieval-Augmented Generation system for Building Information Modeling analysis, validation, and natural language querying.
✨ Overview
The BIM RAG system combines vector database technology with generative AI to provide powerful analysis and querying capabilities for Building Information Models. It enables parameter validation, natural language queries, and comprehensive model analysis.
🚀 Features

📊 Excel Data Processing: Convert BIM data exports to searchable vector format
🏢 Comprehensive Element Support: Analyze walls, doors, windows, slabs and more
✅ Schema Validation: Compare model data against required parameter schemas
💬 Natural Language Querying: Ask questions about your building model in plain English
🔍 Parameter Analysis: Identify missing parameters across all element types
🖥️ Interactive Interface: Command-driven operation with rich visual output
🧠 LLM Integration: Generate natural language responses with Google's Gemini Flash
📝 Detailed Reporting: HTML reports and console visualizations


🛠️ # Installation
bash# Clone the repository
git clone https://github.com/mayureshpawashe/ifc_RAG
cd bim-rag

# Install dependencies
pip install -r requirements.txt

# Configure API key (for LLM functionality)
# Create a .env file with your Google API key:
echo "GOOGLE_API_KEY=your_key_here" > .env
