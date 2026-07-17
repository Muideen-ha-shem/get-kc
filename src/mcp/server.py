"""
Model Context Protocol (MCP) Server for the Ha-Shem AI Support Platform.
Exposes tools for searching the knowledge base, listing products, and diagnostic health checks.
"""

from __future__ import annotations
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Ensure environment variables are loaded from the project root
load_dotenv()

# Initialize the FastMCP server
mcp = FastMCP("Ha-Shem AI Support Platform")


@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """
    Search the Ha-Shem knowledge base for context matching a user query.
    
    Args:
        query: The search term or user question to find in the vector database.
        
    Returns:
        A Markdown-formatted string with the most relevant documentation snippets and source URLs.
    """
    try:
        from src.services.knowledge.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        matches, similarities, parent_urls = service.retrieve_context(query)
        
        if not matches:
            return "No matching documentation found in the knowledge base."
            
        result_lines = ["### Search Results\n"]
        for idx, match in enumerate(matches):
            chunk = match.get("chunk_content", "").strip()
            url = match.get("parent_url", "Unknown Source")
            sim = match.get("similarity", 0.0)
            
            result_lines.append(f"#### Match {idx + 1} (Similarity: {sim:.2f})")
            result_lines.append(f"**Source:** [{url}]({url})")
            result_lines.append(f"```text\n{chunk}\n```\n")
            
        return "\n".join(result_lines)
    except Exception as exc:
        return f"Error executing vector search: {str(exc)}"


@mcp.tool()
def list_products() -> str:
    """
    Retrieve the list of primary products and technology services offered by Ha-Shem.
    
    Returns:
        A structured Markdown summary of Ha-Shem products and services.
    """
    products_markdown = """
# Ha-Shem Limited - Products & Services Portfolio

### 1. Cloud Solutions & Infrastructure
*   **Microsoft 365 Integration:** Setup, migration, and management of modern work productivity tools.
*   **Azure Cloud Infrastructure:** Cloud hosting, server migration, virtual networks, and scalable application hosting.
*   **Active Directory & Identity Management:** Security and access configuration for corporate environments.

### 2. Cybersecurity & Security Operations (SecOps)
*   **Vulnerability Assessments:** Scanning and mitigating network security risks.
*   **Endpoint Detection & Response (EDR):** Comprehensive malware and cyber-attack protection.
*   **Managed Firewalls & Zero Trust Networking:** Secure remote work capabilities.

### 3. Business Automation & Enterprise AI
*   **Support Automation Platforms:** Custom AI agents (such as this RAG platform) to automate customer support workflows.
*   **Custom Software Development:** Modern web systems (React, Node.js) and business APIs (FastAPI).
*   **M365 Power Platform Automation:** Automating repetitive office tasks using Power Automate and Power Apps.

### 4. IT Managed Services & Support
*   **Helpdesk & Desktop Support:** 24/7 technical support for business staff.
*   **Network Audits & Optimization:** Infrastructure design for optimal performance.
"""
    return products_markdown.strip()


@mcp.tool()
def check_service_status() -> str:
    """
    Perform a diagnostic check on the system components to verify operational status.
    Checks the status of Supabase, Groq API, Google Gemini API, and general environment configuration.
    
    Returns:
        A Markdown report summarizing the health and connectivity of required backend services.
    """
    report = ["# System Health & Connectivity Audit\n"]
    
    # 1. Environment Configurations
    google_key = os.getenv("GOOGLE_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    sb_url = os.getenv("SUPABASE_URL")
    sb_key = os.getenv("SUPABASE_KEY")
    
    report.append("### 1. Environment Configuration")
    report.append(f"- **GOOGLE_API_KEY:** {'Present (Validated)' if google_key else 'Missing ❌'}")
    report.append(f"- **GROQ_API_KEY:** {'Present (Validated)' if groq_key else 'Missing ❌'}")
    report.append(f"- **SUPABASE_URL:** {'Present (Validated)' if sb_url else 'Missing ❌'}")
    report.append(f"- **SUPABASE_KEY:** {'Present (Validated)' if sb_key else 'Missing ❌'}\n")
    
    # 2. Database Connectivity
    report.append("### 2. Database Connectivity (Supabase)")
    if not sb_url or not sb_key:
        report.append("- **Status:** Config Missing (Skipped check) ❌")
    else:
        try:
            from src.infrastructure.database.supabase import get_client
            client = get_client()
            # Run a lightweight health check query on the vector table
            test_response = client.table("documentation_chunks").select("id").limit(1).execute()
            report.append("- **Connection:** Success ✅")
            report.append(f"- **Query test:** Retrieved {len(test_response.data)} records from documentation_chunks.")
        except Exception as e:
            report.append(f"- **Connection:** Failed ❌ ({str(e)})")
            
    # 3. Embedding Service Check (Gemini Embeddings API)
    report.append("\n### 3. Embeddings Engine (Google Gemini)")
    if not google_key:
        report.append("- **Status:** Config Missing (Skipped check) ❌")
    else:
        try:
            from src.api.services.embeddings import embed_query
            # Embed a simple test token
            test_vector = embed_query("healthcheck")
            if len(test_vector) == 768:
                report.append("- **Status:** Operational ✅ (Embedding size: 768 dimensions)")
            else:
                report.append(f"- **Status:** Unexpected embedding size: {len(test_vector)} dimensions ⚠️")
        except Exception as e:
            report.append(f"- **Status:** Failed ❌ ({str(e)})")

    # 4. LLM Completion Engine Check (Groq API)
    report.append("\n### 4. Language Generation Engine (Groq API)")
    if not groq_key:
        report.append("- **Status:** Config Missing (Skipped check) ❌")
    else:
        try:
            from groq import Groq
            groq_client = Groq(api_key=groq_key)
            # Create a lightweight completion request
            completion = groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            response_text = completion.choices[0].message.content or ""
            report.append(f"- **Status:** Operational ✅")
            report.append(f"- **API Response:** '{response_text.strip()}'")
        except Exception as e:
            report.append(f"- **Status:** Failed ❌ ({str(e)})")
            
    return "\n".join(report)


if __name__ == "__main__":
    # Start the FastMCP server when script is executed directly
    mcp.run()
