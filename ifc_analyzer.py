import os
import pandas as pd
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from typing import Dict, List, Any, Set, Optional

# Configure console for pretty printing
console = Console()

class IFCDataAnalyzer:
    """Analyze IFC data extracted to Excel files and compare with expected schema"""
    
    def __init__(self, data_folder: str = "data"):
        """Initialize with the data folder containing Excel files"""
        self.data_folder = data_folder
        self.excel_files = [
            os.path.join(data_folder, "ifc_door_export.xlsx"),
            os.path.join(data_folder, "ifc_proxy_export.xlsx"),
            os.path.join(data_folder, "ifc_slab_export.xlsx"),
            os.path.join(data_folder, "ifc_wall_export.xlsx"),
            os.path.join(data_folder, "ifc_wallstandardcase_export.xlsx"),
            os.path.join(data_folder, "ifc_windows_export.xlsx")
        ]
        # Dictionary to store dataframes
        self.dataframes = {}
        # Dictionary to store schema information by element type
        self.schemas = {}
        # Dictionary to store parameter frequency by element type
        self.param_frequencies = {}
        
    def load_excel_files(self) -> None:
        """Load all Excel files into dataframes"""
        with Progress() as progress:
            task = progress.add_task("[cyan]Loading Excel files...", total=len(self.excel_files))
            
            for excel_file in self.excel_files:
                if os.path.exists(excel_file):
                    # Get element type from filename
                    element_type = os.path.basename(excel_file).split('_')[1].split('.')[0]
                    try:
                        # Load Excel file
                        df = pd.read_excel(excel_file)
                        # Store dataframe
                        self.dataframes[element_type] = df
                        console.print(f"[green]Loaded {element_type} data: {len(df)} records[/green]")
                    except Exception as e:
                        console.print(f"[red]Error loading {excel_file}: {e}[/red]")
                else:
                    console.print(f"[yellow]File not found: {excel_file}[/yellow]")
                    
                progress.update(task, advance=1)
    
    def analyze_schema(self) -> None:
        """Analyze the schema of each element type"""
        for element_type, df in self.dataframes.items():
            # Create schema information
            schema = {
                "record_count": len(df),
                "columns": list(df.columns),
                "data_types": {col: str(df[col].dtype) for col in df.columns},
                "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
                "null_percentages": {col: float(df[col].isna().mean() * 100) for col in df.columns},
                "unique_values": {col: int(df[col].nunique()) for col in df.columns},
            }
            
            # Calculate parameter frequency
            total_records = len(df)
            self.param_frequencies[element_type] = {}
            
            for col in df.columns:
                # Count non-null values
                non_null_count = total_records - df[col].isna().sum()
                # Calculate frequency
                frequency = non_null_count / total_records if total_records > 0 else 0
                self.param_frequencies[element_type][col] = frequency
            
            # Store schema
            self.schemas[element_type] = schema
            
            # Print summary
            console.print(f"\n[bold blue]Schema analysis for {element_type}:[/bold blue]")
            console.print(f"Records: {schema['record_count']}")
            console.print(f"Parameters: {len(schema['columns'])}")
            
            # Create table for parameter details
            table = Table(title=f"{element_type} Parameters")
            table.add_column("Parameter", style="cyan")
            table.add_column("Data Type", style="green")
            table.add_column("Null Count", style="yellow")
            table.add_column("Null %", style="yellow")
            table.add_column("Unique Values", style="blue")
            table.add_column("Fill Rate %", style="green")
            
            for col in schema['columns']:
                fill_rate = 100 - schema['null_percentages'][col]
                table.add_row(
                    col,
                    schema['data_types'][col],
                    str(schema['null_counts'][col]),
                    f"{schema['null_percentages'][col]:.1f}%",
                    str(schema['unique_values'][col]),
                    f"{fill_rate:.1f}%"
                )
                
            console.print(table)
            
        return self.schemas
    
    def compare_with_expected_schema(self, expected_schema_file: Optional[str] = None) -> Dict[str, Any]:
        """Compare actual schema with expected schema"""
        result = {
            "missing_parameters": {},
            "extra_parameters": {},
            "low_fill_required": {}
        }
        
        expected_schema = None
        
        # If expected schema file is provided, load it
        if expected_schema_file and os.path.exists(expected_schema_file):
            try:
                with open(expected_schema_file, 'r') as f:
                    expected_schema = json.load(f)
                console.print(f"[green]Loaded expected schema from {expected_schema_file}[/green]")
            except Exception as e:
                console.print(f"[red]Error loading expected schema: {e}[/red]")
        
        # If no expected schema file or loading failed, ask if user wants to define one
        if not expected_schema:
            choice = console.input("[yellow]No expected schema provided. Would you like to define one based on the current data? (y/n)[/yellow] ")
            if choice.lower() in ['y', 'yes']:
                expected_schema = self._create_expected_schema()
            else:
                console.print("[yellow]Skipping schema comparison.[/yellow]")
                return result
        
        # Perform comparison
        console.print("\n[bold blue]Comparing with expected schema:[/bold blue]")
        
        for element_type, expected in expected_schema.items():
            if element_type not in self.schemas:
                console.print(f"[red]Element type {element_type} not found in actual data[/red]")
                continue
                
            actual = self.schemas[element_type]
            
            console.print(f"\n[bold]Element Type: {element_type}[/bold]")
            
            # Compare parameters
            expected_params = set(expected['parameters'])
            actual_params = set(actual['columns'])
            
            missing_params = expected_params - actual_params
            extra_params = actual_params - expected_params
            common_params = expected_params.intersection(actual_params)
            
            # Store results
            result["missing_parameters"][element_type] = list(missing_params)
            result["extra_parameters"][element_type] = list(extra_params)
            
            # Create table for comparison
            table = Table(title=f"{element_type} Parameter Comparison")
            table.add_column("Status", style="cyan")
            table.add_column("Count", style="green")
            table.add_column("Parameters", style="yellow")
            
            table.add_row(
                "Missing Parameters",
                str(len(missing_params)),
                ", ".join(sorted(missing_params)) if missing_params else "None"
            )
            
            table.add_row(
                "Extra Parameters",
                str(len(extra_params)),
                ", ".join(sorted(extra_params)) if extra_params else "None"
            )
            
            table.add_row(
                "Common Parameters",
                str(len(common_params)),
                ", ".join(sorted(common_params)[:5]) + ("..." if len(common_params) > 5 else "")
            )
            
            console.print(table)
            
            # Check for required parameters with low fill rate
            if 'required_parameters' in expected:
                low_fill_required = []
                
                for param in expected['required_parameters']:
                    if param in self.param_frequencies[element_type]:
                        fill_rate = self.param_frequencies[element_type][param] * 100
                        if fill_rate < 90:  # Consider parameters with less than 90% fill rate as problematic
                            low_fill_required.append((param, fill_rate))
                
                if low_fill_required:
                    result["low_fill_required"][element_type] = [(param, rate) for param, rate in low_fill_required]
                    
                    console.print("[red]Required parameters with low fill rate:[/red]")
                    for param, rate in sorted(low_fill_required, key=lambda x: x[1]):
                        console.print(f"  - {param}: {rate:.1f}%")
        
        return result
    
    def _create_expected_schema(self) -> Dict[str, Any]:
        """Create an expected schema based on current data"""
        expected_schema = {}
        
        for element_type, schema in self.schemas.items():
            # Determine which parameters have high fill rate (>80%)
            high_fill_params = [col for col, freq in self.param_frequencies[element_type].items() if freq > 0.8]
            
            # Create expected schema for this element type
            expected_schema[element_type] = {
                "parameters": schema['columns'],
                "required_parameters": high_fill_params,
                "description": f"Expected schema for {element_type} elements"
            }
        
        # Ask user if they want to save this schema
        choice = console.input("[yellow]Do you want to save this expected schema for future use? (y/n)[/yellow] ")
        if choice.lower() in ['y', 'yes']:
            filename = console.input("[yellow]Enter filename to save schema (e.g., expected_schema.json):[/yellow] ")
            try:
                with open(filename, 'w') as f:
                    json.dump(expected_schema, f, indent=2)
                console.print(f"[green]Saved expected schema to {filename}[/green]")
            except Exception as e:
                console.print(f"[red]Error saving schema: {e}[/red]")
        
        return expected_schema
    
    def export_analysis_report(self, output_file: str = "ifc_analysis_report.html") -> str:
        """Export the analysis results to an HTML report"""
        try:
            # Create report HTML
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>IFC Data Analysis Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1, h2, h3 { color: #333; }
                    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                    th, td { padding: 8px; text-align: left; border: 1px solid #ddd; }
                    th { background-color: #f2f2f2; }
                    .missing { color: red; }
                    .extra { color: orange; }
                    .low-fill { background-color: #ffe6e6; }
                    .summary { background-color: #f9f9f9; padding: 10px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <h1>IFC Data Analysis Report</h1>
            """
            
            # Add summary section
            html += "<div class='summary'>"
            html += "<h2>Summary</h2>"
            html += f"<p>Analyzed {len(self.dataframes)} element types from {self.data_folder} folder.</p>"
            
            total_records = sum(len(df) for df in self.dataframes.values())
            html += f"<p>Total records: {total_records}</p>"
            
            html += "<table>"
            html += "<tr><th>Element Type</th><th>Record Count</th><th>Parameter Count</th></tr>"
            
            for element_type, schema in self.schemas.items():
                html += f"<tr><td>{element_type}</td><td>{schema['record_count']}</td><td>{len(schema['columns'])}</td></tr>"
                
            html += "</table>"
            html += "</div>"
            
            # Add detailed sections for each element type
            for element_type, schema in self.schemas.items():
                html += f"<h2>Element Type: {element_type}</h2>"
                
                # Parameter details
                html += "<h3>Parameter Details</h3>"
                html += "<table>"
                html += "<tr><th>Parameter</th><th>Data Type</th><th>Null Count</th><th>Null %</th><th>Unique Values</th><th>Fill Rate %</th></tr>"
                
                for col in schema['columns']:
                    fill_rate = 100 - schema['null_percentages'][col]
                    row_class = " class='low-fill'" if fill_rate < 90 else ""
                    
                    html += f"<tr{row_class}>"
                    html += f"<td>{col}</td>"
                    html += f"<td>{schema['data_types'][col]}</td>"
                    html += f"<td>{schema['null_counts'][col]}</td>"
                    html += f"<td>{schema['null_percentages'][col]:.1f}%</td>"
                    html += f"<td>{schema['unique_values'][col]}</td>"
                    html += f"<td>{fill_rate:.1f}%</td>"
                    html += "</tr>"
                    
                html += "</table>"
            
            html += """
            </body>
            </html>
            """
            
            # Write to file
            with open(output_file, 'w') as f:
                f.write(html)
                
            console.print(f"[green]Exported analysis report to {output_file}[/green]")
            return output_file
            
        except Exception as e:
            console.print(f"[red]Error exporting report: {e}[/red]")
            return ""

    def run_analysis(self, expected_schema_file: Optional[str] = None, output_file: str = "ifc_analysis_report.html") -> Dict:
        """Run the full analysis and return results"""
        console.print(Panel.fit("[bold cyan]IFC Data Analyzer[/bold cyan]"))
        
        # Load and analyze data
        self.load_excel_files()
        schemas = self.analyze_schema()
        
        # Compare with expected schema if provided
        comparison_results = {}
        if expected_schema_file:
            comparison_results = self.compare_with_expected_schema(expected_schema_file)
        
        # Export report
        report_path = self.export_analysis_report(output_file)
        
        console.print(Panel.fit("[bold green]Analysis complete[/bold green]"))
        
        return {
            "schemas": schemas,
            "comparison": comparison_results,
            "report_path": report_path
        }


# Standalone function to be imported in RAG
def analyze_ifc_data(data_folder: str = "data", 
                     expected_schema_file: Optional[str] = None,
                     output_file: str = "ifc_analysis_report.html") -> Dict:
    """Analyze IFC data and return results"""
    analyzer = IFCDataAnalyzer(data_folder=data_folder)
    return analyzer.run_analysis(expected_schema_file, output_file)


def main():
    """Main function to run the IFC data analyzer as a standalone script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze IFC data and compare with expected schema")
    parser.add_argument("--data-folder", type=str, default="data", help="Folder containing Excel files (default: data)")
    parser.add_argument("--expected-schema", type=str, help="JSON file containing expected schema")
    parser.add_argument("--output", type=str, default="ifc_analysis_report.html", help="Output file for analysis report")
    args = parser.parse_args()
    
    # Run analysis
    analyze_ifc_data(args.data_folder, args.expected_schema, args.output)


if __name__ == "__main__":
    main()