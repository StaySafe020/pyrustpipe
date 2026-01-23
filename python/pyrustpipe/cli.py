"""Command-line interface for pyrustpipe"""

import click
from pathlib import Path
import sys
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from pyrustpipe import Validator, Schema, Field
from pyrustpipe.schema import Schema
import importlib.util


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """pyrustpipe - Fast data validation with Rust backend"""
    pass


@main.command()
@click.option("--rules", "-r", required=True, type=click.Path(exists=True), help="Python file with validation rules")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), help="Input CSV file to validate")
@click.option("--s3", type=str, help="S3 URI (s3://bucket/key) to validate")
@click.option("--output", "-o", type=click.Path(), help="Output file for validation results")
@click.option("--parallel/--no-parallel", default=True, help="Enable parallel processing")
@click.option("--chunk-size", default=10000, type=int, help="Chunk size for processing")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def validate(rules, input_path, s3, output, parallel, chunk_size, verbose):
    """Validate data using defined rules"""
    
    console.print(f"[bold blue]pyrustpipe validator[/bold blue]")
    console.print(f"Rules: {rules}")
    
    # Load rules from Python file
    try:
        schema = load_rules_from_file(rules)
    except Exception as e:
        console.print(f"[bold red]Error loading rules:[/bold red] {e}", style="red")
        sys.exit(1)
    
    # Create validator
    validator = Validator(schema=schema, parallel=parallel, chunk_size=chunk_size)
    
    # Validate data
    try:
        if input_path:
            console.print(f"Validating local file: {input_path}")
            result = validator.validate_csv(input_path, output_path=output)
        elif s3:
            # Parse S3 URI
            if not s3.startswith("s3://"):
                console.print("[bold red]S3 URI must start with s3://[/bold red]")
                sys.exit(1)
            
            s3_path = s3[5:]  # Remove s3://
            parts = s3_path.split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
            
            console.print(f"Validating S3: bucket={bucket}, key={key}")
            result = validator.validate_s3(bucket, key)
        else:
            console.print("[bold red]Either --input or --s3 must be provided[/bold red]")
            sys.exit(1)
        
        # Display results
        display_results(result, verbose)
        
        # Exit with error code if validation failed
        sys.exit(0 if result.is_valid() else 1)
        
    except Exception as e:
        console.print(f"[bold red]Validation error:[/bold red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@main.command()
@click.argument("output", type=click.Path())
@click.option("--name", default="validation_rules", help="Schema name")
def init(output, name):
    """Initialize a new validation rules file"""
    
    template = f'''"""
Validation rules for {name}
"""

from pyrustpipe import Schema, Field, validate


# Define schema
{name}_schema = Schema({{
    "id": Field(int, required=True, min=1),
    "name": Field(str, required=True, min_length=2, max_length=100),
    "email": Field(str, required=True, pattern=r"^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$"),
    "age": Field(int, min=0, max=150),
    "balance": Field(float, min=0.0),
}})


# Custom validation rules (optional)
@validate
def check_age_consistency(row):
    """Ensure age is consistent with other fields"""
    if hasattr(row, "age") and hasattr(row, "birthdate"):
        # Add custom logic here
        pass
    return True


@validate(name="balance_check")
def check_balance_positive(row):
    """Ensure balance is non-negative"""
    assert row.balance >= 0, "Balance must be non-negative"


# Export the schema for CLI usage
schema = {name}_schema
'''
    
    output_path = Path(output)
    if output_path.exists():
        if not click.confirm(f"{output} already exists. Overwrite?"):
            console.print("Cancelled.")
            return
    
    output_path.write_text(template)
    console.print(f"[bold green]Created validation rules file:[/bold green] {output}")
    console.print(f"\nUsage: pyrustpipe validate --rules {output} --input data.csv")


def load_rules_from_file(rules_path: str) -> Schema:
    """Load validation rules from Python file"""
    spec = importlib.util.spec_from_file_location("rules_module", rules_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load rules from {rules_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Try to get schema from module
    if hasattr(module, "schema"):
        return module.schema
    else:
        raise ValueError("Rules file must define a 'schema' variable")


def display_results(result, verbose: bool = False):
    """Display validation results in a nice format"""
    
    # Summary table
    table = Table(title="Validation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Rows", str(result.total_rows))
    table.add_row("Valid Rows", f"[green]{result.valid_count}[/green]")
    table.add_row("Invalid Rows", f"[red]{result.invalid_count}[/red]")
    table.add_row("Success Rate", f"{result.success_rate():.2f}%")
    
    console.print(table)
    
    # Error details if verbose or if there are errors
    if verbose and result.errors:
        console.print("\n[bold yellow]Errors:[/bold yellow]")
        
        error_table = Table()
        error_table.add_column("Row", style="cyan")
        error_table.add_column("Field", style="blue")
        error_table.add_column("Rule", style="magenta")
        error_table.add_column("Message", style="red")
        
        # Show first 20 errors
        for error in result.errors[:20]:
            error_table.add_row(
                str(error.row_index),
                error.field,
                error.rule,
                error.message
            )
        
        console.print(error_table)
        
        if len(result.errors) > 20:
            console.print(f"\n[yellow]... and {len(result.errors) - 20} more errors[/yellow]")


if __name__ == "__main__":
    main()
