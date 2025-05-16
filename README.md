# 🏗️ **BIM RAG System** 🤖  
*A Retrieval-Augmented Generation system for Building Information Modeling analysis, validation, and natural language querying.*

---

## ✨ **Overview**  
The **BIM RAG System** combines vector database technology with generative AI to provide powerful analysis and querying capabilities for **Building Information Models**. It enables **parameter validation**, **natural language queries**, and **comprehensive model analysis**.

---

## 🚀 **Features**

- 📊 **Excel Data Processing**: Convert BIM data exports to searchable vector format  
- 🏢 **Comprehensive Element Support**: Analyze walls, doors, windows, slabs and more  
- ✅ **Schema Validation**: Compare model data against required parameter schemas  
- 💬 **Natural Language Querying**: Ask questions about your building model in plain English  
- 🔍 **Parameter Analysis**: Identify missing parameters across all element types  
- 🖥️ **Interactive Interface**: Command-driven operation with rich visual output  
- 🧠 **LLM Integration**: Generate natural language responses with Google's Gemini Flash  
- 📝 **Detailed Reporting**: HTML reports and console visualizations  

---

## 🛠️ **Installation**

```bash
# Clone the repository
git clone https://github.com/yourusername/bim-rag.git
cd bim-rag

# Install dependencies
pip install -r requirements.txt

# Configure API key (for LLM functionality)
# Create a .env file with your Google API key:
echo "GOOGLE_API_KEY=your_key_here" > .env
```

---

## 📋 **Usage**

### **Data Preparation**
Export your BIM data to Excel files and place them in the `data` folder:

- 🚪 `ifc_door_export.xlsx`  
- 🧱 `ifc_wall_export.xlsx`  
- 🛤️ `ifc_slab_export.xlsx`  
- 🪟 `ifc_windows_export.xlsx`  
- 📁 ...etc.

---

### **Convert Excel Data to Vector Database**
```bash
python RAG.py --convert
```

---

### **Analyze Model Data**
```bash
python RAG.py --analyze
```

---

### **Validate Against Schema**
```bash
python RAG.py --compare expected_schema.json
```

---

### **Check Missing Parameters by Element Type**
```bash
python RAG.py --wall-params
python RAG.py --door-params
python RAG.py --window-params
python RAG.py --slab-params
```

---

### **Start Interactive Query Mode**
```bash
python RAG.py
```

---

## 💻 **Interactive Commands**

While in **interactive mode**, you can use the following commands:

- 🔎 `analyze`: Run IFC data analysis  
- 🔄 `compare <schema_file>`: Compare data against schema  
- 🧱 `wall parameters`: Show missing wall parameters  
- 🚪 `door parameters`: Show missing door parameters  
- 🪟 `window parameters`: Show missing window parameters  
- 🛤️ `slab parameters`: Show missing slab parameters  
- 📊 `analysis summary`: Show overall analysis summary  
- ❌ `exit` or `quit`: End the session  

---

## 📝 **Schema Format**

Your schema should be a **JSON** file structured like this:

```json
{
  "door": {
    "parameters": [
      "GlobalId", "Name", "Description", "OverallHeight", "OverallWidth"
    ],
    "required_parameters": [
      "GlobalId", "Name", "OverallHeight", "OverallWidth"
    ],
    "description": "Expected schema for door elements"
  },
  "wall": {
    "parameters": [
      "GlobalId", "Name", "Description", "Length", "Width", "Height"
    ],
    "required_parameters": [
      "GlobalId", "Name", "Length", "Width", "Height"
    ],
    "description": "Expected schema for wall elements"
  }
}
```

---

## 💻 **System Requirements**

- ✅ Python **3.8+**  
- ✅ Minimum **4GB RAM** (8GB recommended for larger models)  
- ✅ All dependencies listed in `requirements.txt`  

---

## 🏗️ **Architecture**

The system is composed of several key modules:

- 📥 **ExcelToChromaConverter**: Converts Excel files to vector embeddings  
- 🔎 **BIMQueryEngine**: Handles vector search and relevance scoring  
- 🧠 **GeminiRAGSystem**: Integrates LLM capabilities with retrieved context  
- 🔧 **IFC Analyzer**: Specialized module for BIM data analysis  

---

## 💡 **Examples**

### **Natural Language Queries**

Ask questions like:

- 🚪 *"How many external doors are in the model?"*  
- 🧱 *"What’s the average height of walls?"*  
- 🪟 *"Which windows have thermal transmittance values?"*  
- 🏗️ *"List all load-bearing walls."*  

---

### **Parameter Analysis Commands**
Check for missing parameters:
```bash
> wall parameters
```
**Wall Parameter Analysis Summary:**  
**Wall Type**: `wall`  
**Missing Parameters**: `FireRating`, `ThermalTransmittance`

---

## 🔮 **Development Roadmap**

- ✨ Parameter value validation  
- 📊 Automated model health scoring  
- 📈 Visual parameter explorer  
- 🔄 Multi-model comparison capabilities  
- 🤝 Integration with collaboration platforms  

---

## 📜 **License**
**MIT License**

---

## 🙏 **Acknowledgments**

- 🔤 **SentenceTransformer** for vector embeddings  
- 🗄️ **ChromaDB** for vector database functionality  
- 🤖 **Google's Generative AI** for LLM capabilities