from fastmcp import FastMCP
import random
import json

#create the fastmcp server instance
mcp = FastMCP("Simple calculator Server")

#tool: add two numbers 
@mcp.tool
def add(a: int, b:int)-> int:
    """ 
    Add two numbers together.
    Args :
    a: first number
    b: second number
    returns:
    the sum of a and b
    """
    return a+b

#Tool: generate a random number
@mcp.tool
def random_number(min_val: int=1, max_val: int = 100)-> int:
    """Generate a random number within a range.
    Args:
        min_val: Minimum value (default: 1)
        max_val: Maximum value (default: 100)

    Returns:
        A random integer between min_val and max_val
    """
    return random.randint(min_val, max_val)

# Resource: Server information
@mcp.resource("info://server")
def server_info() -> str:
    """Get information about this server."""
    info = {
        "name": "Simple Calculator Server",
        "version": "1.0.0",
        "description": "A basic MCP server with math tools",
        "tools": ["add", "random_number"],
        "author": "Divya"
    }
    return json.dumps(info, indent=2)


# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000) #streamable http
    #mcp.run(default transport - stdio)