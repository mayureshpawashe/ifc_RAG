import os
import json
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table
from dotenv import load_dotenv
import google.generativeai as genai

# Import the IFC analyzer module
import ifc_analyzer

# Load environment variables (for Gemini API key)
load_dotenv()

# Configure console for pretty printing
console = Console()

class ExcelToChromaConverter:
    """Convert Excel files to ChromaDB collections for RAG"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize the converter with a persistence directory"""
        self.persist_directory = persist_directory
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # Lightweight embedding model
        )
        
        # Create the persistence directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        console.print(f"[green]Initialized ChromaDB at {persist_directory}[/green]")
        
    def prepare_documents_from_excel(self, excel_file_path: str) -> List[Dict[str, Any]]:
        """Prepare documents from an Excel file for embedding into ChromaDB"""
        try:
            # Check if file exists
            if not os.path.exists(excel_file_path):
                console.print(f"[red]Error: File {excel_file_path} not found[/red]")
                return []
                
            # Read the Excel file
            df = pd.read_excel(excel_file_path)
            
            # Handle missing values
            df = df.fillna("")
            
            # Get element type from filename (e.g., "ifc_wall_export.xlsx" -> "wall")
            element_type = os.path.basename(excel_file_path).split('_')[1].split('.')[0]
            
            documents = []
            
            # Process each row as a document
            for idx, row in df.iterrows():
                # Convert row to dictionary
                row_dict = row.to_dict()
                
                # Add element type to metadata
                row_dict["ElementType"] = element_type
                
                # Create a text representation of the document
                content = " ".join([f"{key}: {value}" for key, value in row_dict.items() if str(value).strip()])
                
                # Create document with metadata
                document = {
                    "id": f"{element_type}_{idx}",
                    "content": content,
                    "metadata": row_dict
                }
                
                documents.append(document)
                
            return documents
            
        except Exception as e:
            console.print(f"[red]Error processing {excel_file_path}: {e}[/red]")
            return []
        
    def create_collection(self, collection_name: str, documents: List[Dict[str, Any]]) -> None:
        """Create a collection in ChromaDB with the given documents"""
        # Check if collection already exists
        collection_exists = collection_name in [col.name for col in self.client.list_collections()]
        
        if collection_exists:
            # Ask user what to do
            console.print(f"[blue]Collection '{collection_name}' already exists.[/blue]")
            choice = console.input("\n[bold yellow]Use existing collection or create new one? (existing/new):[/bold yellow] ")
            
            if choice.lower() in ["new", "n"]:
                self.client.delete_collection(name=collection_name)
                console.print(f"[yellow]Deleted existing collection: {collection_name}[/yellow]")
            else:
                console.print(f"[green]Using existing collection: {collection_name}[/green]")
                return  # Keep existing collection and don't add documents
        
        # Create new collection
        console.print(f"[green]Creating new collection: {collection_name}[/green]")
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        
        # Add documents in batches to avoid memory issues
        batch_size = 100
        with Progress() as progress:
            task = progress.add_task("[cyan]Adding documents...", total=len(documents))
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                
                # Extract data for the batch
                ids = [doc["id"] for doc in batch]
                contents = [doc["content"] for doc in batch]
                metadatas = [doc["metadata"] for doc in batch]
                
                # Add to collection
                collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas
                )
                
                progress.update(task, advance=len(batch))
            
        console.print(f"[green]Added {len(documents)} documents to collection {collection_name}[/green]")
        
    def process_excel_files(self, excel_files: List[str], collection_name: str) -> None:
        """Process multiple Excel files and add them to a single collection"""
        all_documents = []
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing Excel files...", total=len(excel_files))
            
            for excel_file in excel_files:
                console.print(f"[blue]Processing {excel_file}...[/blue]")
                documents = self.prepare_documents_from_excel(excel_file)
                all_documents.extend(documents)
                console.print(f"[green]Extracted {len(documents)} documents from {excel_file}[/green]")
                progress.update(task, advance=1)
                
        # Create collection with all documents
        self.create_collection(collection_name, all_documents)


class BIMQueryEngine:
    """A query engine for answering questions about BIM data"""
    
    def __init__(self, collection_name: str = "ifc_elements", persist_directory: str = "./chroma_db"):
        """Initialize the query engine with a ChromaDB collection"""
        # Set up ChromaDB
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Try to get the collection
        try:
            # Check if collection exists
            if collection_name in [col.name for col in self.client.list_collections()]:
                self.collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                console.print(f"[green]Connected to existing collection: {collection_name}[/green]")
            else:
                console.print(f"[yellow]Collection '{collection_name}' does not exist.[/yellow]")
                console.print(f"[yellow]Please run with --convert first to create and populate it.[/yellow]")
                raise ValueError(f"Collection '{collection_name}' does not exist")
        except Exception as e:
            console.print(f"[red]Error connecting to collection {collection_name}: {e}[/red]")
            raise e
    
    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """Query the collection with a natural language query"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        formatted_results = []
        for i in range(len(results["documents"][0])):
            # Properly handle distance to ensure positive relevance scores
            distance = results["distances"][0][i]
            
            # Normalize the distance to ensure a positive score between 0 and 1
            # This handles any distance metric (cosine, euclidean, etc.)
            if distance > 1:
                # For distances > 1 (like euclidean), use an exponential decay formula
                relevance = 1 / (1 + distance)
            else:
                # For distances <= 1 (like cosine), use linear conversion
                relevance = 1 - distance
                
            # Ensure the score is always positive
            relevance = max(0, min(1, relevance))
            
            result = {
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": relevance  # Properly normalized relevance score
            }
            formatted_results.append(result)
            
        return {
            "query": query_text,
            "results": formatted_results
        }


class GeminiRAGSystem:
    """RAG system using ChromaDB embeddings and Gemini Flash LLM"""
    
    def __init__(self, collection_name: str = "ifc_elements", persist_directory: str = "./chroma_db"):
        """Initialize the RAG system with a ChromaDB collection and Gemini API"""
        # Set up the query engine
        self.query_engine = BIMQueryEngine(collection_name, persist_directory)
        
        # Store for analysis results
        self.analysis_results = None
        self.analysis_results_path = "analysis_results.json"
        
        # Load previous analysis results if they exist
        if os.path.exists(self.analysis_results_path):
            try:
                with open(self.analysis_results_path, 'r') as f:
                    self.analysis_results = json.load(f)
                console.print(f"[green]Loaded previous analysis results from {self.analysis_results_path}[/green]")
            except Exception as e:
                console.print(f"[yellow]Could not load previous analysis results: {e}[/yellow]")
        
        # Set up Gemini API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            console.print("[yellow]Warning: GOOGLE_API_KEY not found in environment variables.[/yellow]")
            console.print("[yellow]To enable LLM integration, set the GOOGLE_API_KEY environment variable.[/yellow]")
            console.print("[yellow]You can create a .env file with GOOGLE_API_KEY=your_key_here[/yellow]")
            self.llm_enabled = False
        else:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.llm_enabled = True
                console.print("[green]Gemini Flash model initialized successfully[/green]")
            except Exception as e:
                console.print(f"[red]Error initializing Gemini model: {e}[/red]")
                console.print("[yellow]Falling back to non-LLM mode[/yellow]")
                self.llm_enabled = False
    
    def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate a response using Gemini model with retrieved context"""
        if not self.llm_enabled:
            # Provide a fallback response with the retrieved context
            formatted_context = "\n\n".join([
                f"Document {i+1} (Relevance: {doc['score']:.2f}):\n{doc['content']}"
                for i, doc in enumerate(context)
            ])
            return f"LLM integration is disabled. Here are the most relevant results:\n\n{formatted_context}"
            
        try:
            # Format the context for the prompt
            formatted_context = "\n\n".join([
                f"Document {i+1} (Relevance: {doc['score']:.2f}):\n{doc['content']}"
                for i, doc in enumerate(context)
            ])
            
            # Prepare the prompt
            prompt = f"""
            You are an expert Building Information Modeling (BIM) assistant that helps users understand building models.
            Answer the question based ONLY on the provided context about the building model.
            If you cannot answer based on the context, say so clearly.
            
            CONTEXT:
            {formatted_context}
            
            QUESTION:
            {query}
            
            ANSWER:
            """
            
            # Generate response
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            console.print(f"[red]Error generating response with Gemini: {e}[/red]")
            return f"Error generating response with Gemini: {e}\n\nHere are the most relevant results:\n\n{formatted_context}"
    
    def answer_question(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Answer a question about the building model"""
        # Check if this is a question about analysis results for specific element types
        if "missing" in query.lower() and "parameters" in query.lower():
            # Wall parameters
            if "wall" in query.lower():
                return self.answer_missing_element_parameters("wall")
            # Door parameters
            elif "door" in query.lower():
                return self.answer_missing_element_parameters("door")
            # Window parameters
            elif "window" in query.lower():
                return self.answer_missing_element_parameters("window")
            # Slab parameters
            elif "slab" in query.lower():
                return self.answer_missing_element_parameters("slab")
        
        # Regular RAG flow
        # Step 1: Retrieve relevant documents
        console.print(f"\n[bold blue]Retrieving information for: [/bold blue][yellow]{query}[/yellow]")
        query_results = self.query_engine.query(query, n_results)
        retrieved_docs = query_results["results"]
        
        # Step 2: Generate response with LLM if available
        if self.llm_enabled:
            console.print("[bold blue]Generating response with Gemini Flash...[/bold blue]")
            response = self.generate_response(query, retrieved_docs)
        else:
            response = "LLM integration is disabled. Here are the most relevant results from your building model data."
        
        # Return the full result
        return {
            "query": query,
            "response": response,
            "sources": retrieved_docs
        }
    
    def answer_missing_element_parameters(self, element_type: str) -> Dict[str, Any]:
        """Generalized function to answer questions about missing parameters for any element type"""
        if not self.analysis_results or 'comparison' not in self.analysis_results:
            return {
                "query": f"What are the missing {element_type} parameters?",
                "response": f"No analysis results available. Please run the analysis first using the 'analyze' command.",
                "sources": []
            }
        
        # Extract parameters from analysis results
        missing_params = self.analysis_results['comparison'].get('missing_parameters', {})
        element_params = {}
        
        # Look for element-related parameters
        for elem_type, params in missing_params.items():
            if element_type in elem_type.lower():
                element_params[elem_type] = params
        
        if not element_params:
            response = f"No missing {element_type} parameters were found in the analysis."
        else:
            # Create response text
            response = f"Here are the missing {element_type} parameters based on the analysis:\n\n"
            for elem_type, params in element_params.items():
                response += f"For {elem_type}:\n"
                if params:
                    for param in params:
                        response += f"- {param}\n"
                else:
                    response += "- No missing parameters\n"
                response += "\n"
        
        return {
            "query": f"What are the missing {element_type} parameters?",
            "response": response,
            "sources": []  # No sources needed as we're using analysis results directly
        }
    
    def answer_missing_wall_parameters(self) -> Dict[str, Any]:
        """Specific function to answer questions about missing wall parameters"""
        # This now just calls the generalized function
        return self.answer_missing_element_parameters("wall")
    
    def run_ifc_analysis(self, data_folder: str = "data", expected_schema_file: Optional[str] = None, output_file: str = "ifc_analysis_report.html") -> Dict:
        """Run IFC data analysis from within the RAG system"""
        console.print(Panel.fit("[bold cyan]Running IFC Data Analysis[/bold cyan]"))
        
        try:
            # Run the analysis using the imported module
            results = ifc_analyzer.analyze_ifc_data(
                data_folder=data_folder,
                expected_schema_file=expected_schema_file,
                output_file=output_file
            )
            
            # Save the results to a file for later querying
            if results:
                console.print("[green]Analysis completed successfully![/green]")
                console.print(f"Report saved to: {results['report_path']}")
                
                # Store results for querying
                self.analysis_results = results
                
                # Save results to a file
                with open(self.analysis_results_path, 'w') as f:
                    json.dump(results, f, indent=2)
                console.print(f"[green]Analysis results saved to {self.analysis_results_path} for querying[/green]")
                
                # Print a summary of parameters
                self.display_analysis_summary()
            else:
                console.print("[red]Analysis failed![/red]")
                
            return results
        except Exception as e:
            console.print(f"[red]Error running analysis: {e}[/red]")
            return {"error": str(e)}
    
    def display_element_parameter_summary(self, element_type: str):
        """Display a summary of parameters for specific element types from the analysis results"""
        if not self.analysis_results or 'comparison' not in self.analysis_results:
            console.print(f"[yellow]No analysis results available for {element_type} parameters.[/yellow]")
            return
        
        missing_params = self.analysis_results['comparison'].get('missing_parameters', {})
        element_types = [elem_type for elem_type in missing_params.keys() if element_type in elem_type.lower()]
        
        if not element_types:
            console.print(f"[green]No {element_type} types found in the analysis.[/green]")
            return
        
        console.print(f"[bold cyan]{element_type.capitalize()} Parameter Analysis Summary:[/bold cyan]")
        
        table = Table(title=f"Missing {element_type.capitalize()} Parameters")
        table.add_column(f"{element_type.capitalize()} Type", style="cyan")
        table.add_column("Missing Parameters", style="yellow")
        
        for elem_type in element_types:
            params = missing_params.get(elem_type, [])
            param_str = "\n".join(params) if params else "None"
            table.add_row(elem_type, param_str)
        
        console.print(table)
    
    def display_wall_parameter_summary(self):
        """Display a summary of wall parameters from the analysis results"""
        self.display_element_parameter_summary("wall")
    
    def display_door_parameter_summary(self):
        """Display a summary of door parameters from the analysis results"""
        self.display_element_parameter_summary("door")
    
    def display_window_parameter_summary(self):
        """Display a summary of window parameters from the analysis results"""
        self.display_element_parameter_summary("window")
        
    def display_slab_parameter_summary(self):
        """Display a summary of slab parameters from the analysis results"""
        self.display_element_parameter_summary("slab")
    
    def display_analysis_summary(self):
        """Display a summary of all parameters from the analysis results"""
        if not self.analysis_results or 'comparison' not in self.analysis_results:
            console.print("[yellow]No analysis results available.[/yellow]")
            return
        
        missing_params = self.analysis_results['comparison'].get('missing_parameters', {})
        
        if not missing_params:
            console.print("[green]No missing parameters found in the analysis.[/green]")
            return
        
        console.print("[bold cyan]Element Parameter Analysis Summary:[/bold cyan]")
        
        # First display overall metrics
        total_missing = sum(len(params) for params in missing_params.values())
        console.print(f"Total missing parameters: {total_missing}")
        console.print(f"Element types analyzed: {len(missing_params)}")
        
        # Then show all element types in a table
        table = Table(title="Missing Parameters by Element Type")
        table.add_column("Element Type", style="cyan")
        table.add_column("Missing Parameters Count", style="yellow")
        table.add_column("Missing Parameters", style="green")
        
        for elem_type, params in missing_params.items():
            param_count = len(params)
            param_str = ", ".join(params) if params else "None"
            table.add_row(elem_type, str(param_count), param_str)
        
        console.print(table)
        
        # Ask if the user wants to see details for specific element types
        console.print("\n[bold cyan]Type 'wall parameters', 'door parameters', 'window parameters', or 'slab parameters' for detailed view[/bold cyan]")
    
    def interactive_mode(self):
        """Run an interactive session where the user can ask questions"""
        console.print(Panel.fit(
            "[bold green]Building Model RAG System[/bold green]\n"
            "Ask questions about your building model using natural language.\n"
            "Type 'exit' or 'quit' to end the session.\n"
            "Special commands:\n"
            "- 'analyze': Run IFC data analysis\n"
            "- 'compare <schema_file>': Compare IFC data with expected schema\n"
            "- 'wall parameters': Show missing wall parameters\n"
            "- 'door parameters': Show missing door parameters\n"
            "- 'window parameters': Show missing window parameters\n"
            "- 'slab parameters': Show missing slab parameters\n"
            "- 'analysis summary': Show overall analysis summary"
        ))
        
        while True:
            query = console.input("\n[bold yellow]Ask a question:[/bold yellow] ")
            
            if query.lower() in ["exit", "quit", "q"]:
                console.print("[bold green]Thank you for using the Building RAG system![/bold green]")
                break
                
            # Special commands
            if query.lower() == "analyze":
                self.run_ifc_analysis()
                continue
                
            if query.lower().startswith("compare "):
                # Extract schema file path
                parts = query.split(" ", 1)
                if len(parts) > 1:
                    schema_file = parts[1].strip()
                    self.run_ifc_analysis(expected_schema_file=schema_file)
                else:
                    console.print("[yellow]Please specify a schema file path.[/yellow]")
                continue
                
            if query.lower() in ["wall parameters", "wall params", "missing wall parameters"]:
                self.display_wall_parameter_summary()
                continue
                
            if query.lower() in ["door parameters", "door params", "missing door parameters"]:
                self.display_door_parameter_summary()
                continue
                
            if query.lower() in ["window parameters", "window params", "missing window parameters"]:
                self.display_window_parameter_summary()
                continue
                
            if query.lower() in ["slab parameters", "slab params", "missing slab parameters"]:
                self.display_slab_parameter_summary()
                continue
                
            if query.lower() in ["analysis summary", "summary"]:
                self.display_analysis_summary()
                continue
                
            try:
                result = self.answer_question(query)
                
                # Print the response
                console.print(Panel(
                    result["response"],
                    title="[bold green]Answer[/bold green]",
                    expand=False
                ))
                
                # Ask if user wants to see sources (if there are any)
                if result["sources"]:
                    show_sources = console.input("\n[bold cyan]Show sources? (y/n):[/bold cyan] ")
                    if show_sources.lower() in ["y", "yes"]:
                        console.print("[bold blue]Sources:[/bold blue]")
                        for i, doc in enumerate(result["sources"]):
                            console.print(Panel(
                                f"{doc['content'][:500]}...",
                                title=f"[bold]Source {i+1} (Relevance: {doc['score']:.2f})[/bold]",
                                expand=False
                            ))
                        
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")


def main():
    """Main function to run the Excel to ChromaDB conversion and RAG system"""
    parser = argparse.ArgumentParser(description="Convert Excel files to ChromaDB and query the data")
    parser.add_argument("--convert", action="store_true", help="Convert Excel files to ChromaDB")
    parser.add_argument("--query", action="store_true", help="Query the ChromaDB collection")
    parser.add_argument("--analyze", action="store_true", help="Run IFC data analysis")
    parser.add_argument("--compare", type=str, help="Compare IFC data with expected schema file")
    parser.add_argument("--wall-params", action="store_true", help="Display missing wall parameters")
    parser.add_argument("--door-params", action="store_true", help="Display missing door parameters")
    parser.add_argument("--window-params", action="store_true", help="Display missing window parameters")
    parser.add_argument("--slab-params", action="store_true", help="Display missing slab parameters")
    parser.add_argument("--data-folder", type=str, default="data", help="Folder containing Excel files (default: data)")
    parser.add_argument("--output", type=str, default="ifc_analysis_report.html", help="Output file for analysis report")
    args = parser.parse_args()
    
    # Default to query mode if no arguments specified
    if not (args.convert or args.query or args.analyze or args.compare or args.wall_params or 
            args.door_params or args.window_params or args.slab_params):
        args.query = True
    
    # Excel files to process - stored in the data folder
    data_folder = args.data_folder
    excel_files = [
        os.path.join(data_folder, "ifc_door_export.xlsx"),
        os.path.join(data_folder, "ifc_proxy_export.xlsx"),
        os.path.join(data_folder, "ifc_slab_export.xlsx"),
        os.path.join(data_folder, "ifc_wall_export.xlsx"),
        os.path.join(data_folder, "ifc_wallstandardcase_export.xlsx"),
        os.path.join(data_folder, "ifc_windows_export.xlsx")
    ]
    
    collection_name = "ifc_elements"
    persist_directory = "./chroma_db"
    
    if args.convert:
        # Check if files exist
        missing_files = [f for f in excel_files if not os.path.exists(f)]
        if missing_files:
            console.print(f"[yellow]Warning: The following files were not found:[/yellow]")
            for f in missing_files:
                console.print(f"[yellow]  - {f}[/yellow]")
            
            if all(not os.path.exists(f) for f in excel_files):
                console.print(f"[red]Error: No Excel files found in the {data_folder} folder.[/red]")
                console.print(f"[yellow]Make sure your Excel files are in the {data_folder} folder or specify a different folder with --data-folder.[/yellow]")
                return
        
        console.print(Panel.fit("[bold cyan]Step 1: Converting Excel files to ChromaDB[/bold cyan]"))
        converter = ExcelToChromaConverter(persist_directory)
        
        # Only process files that exist
        existing_files = [f for f in excel_files if os.path.exists(f)]
        if existing_files:
            converter.process_excel_files(existing_files, collection_name)
        else:
            console.print("[red]No valid Excel files to process.[/red]")
            return
    
    # Create RAG instance for analyze, parameter checks or query operations
    if (args.analyze or args.compare or args.wall_params or args.door_params or 
            args.window_params or args.slab_params or args.query):
        try:
            # Initialize the RAG system
            rag = GeminiRAGSystem(collection_name, persist_directory)
            
            if args.analyze:
                rag.run_ifc_analysis(data_folder=args.data_folder, output_file=args.output)
                
            if args.compare:
                rag.run_ifc_analysis(
                    data_folder=args.data_folder,
                    expected_schema_file=args.compare,
                    output_file=args.output
                )
                
            if args.wall_params:
                rag.display_wall_parameter_summary()
                
            if args.door_params:
                rag.display_door_parameter_summary()
                
            if args.window_params:
                rag.display_window_parameter_summary()
                
            if args.slab_params:
                rag.display_slab_parameter_summary()
                
            if args.query:
                rag.interactive_mode()
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Make sure you've run the conversion step first if querying, and that the IFC analyzer module is available.[/yellow]")


if __name__ == "__main__":
    main()